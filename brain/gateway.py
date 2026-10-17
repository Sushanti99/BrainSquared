"""The BrainSquared gateway: one MCP endpoint that every agent goes through.

The gateway holds the connections to the user's apps (Gmail, Notion, Slack,
...) itself. Each agent gets its own URL, `/a/<token>/mcp`, and only sees the
tools its rules in `system/access.yaml` allow. Every call is checked against
those rules at call time — so revoking an agent takes effect on its very next
call — and written to `system/audit.jsonl`.

    agent ──► /a/<token>/mcp ──► rules + audit ──► app MCP servers
                                       │
                                       └──► get_context (vault folders it may read)
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import anyio
import anyio.to_thread
from mcp import ClientSession, types
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from mcp.server.lowlevel import Server
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from brain import mcp_config, policy
from brain.vault import read_vault

logger = logging.getLogger("brain.gateway")

DEFAULT_GATEWAY_PORT = 6684
TOOL_SEP = "__"
CONTEXT_TOOL = "get_context"
BACKEND_START_TIMEOUT = 90  # npx-based servers may download on first start

APP_LABELS = {
    "google": "Gmail + Calendar",
    "github": "GitHub",
    "notion": "Notion",
    "slack": "Slack",
    "linear": "Linear",
}

Approver = Callable[[str, str, str, dict[str, Any]], bool]


# ── app backends ──────────────────────────────────────────────────────────────

@dataclass
class Backend:
    """How the gateway reaches one app: a local stdio server or a remote URL."""

    app: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)


def backends_from_env(environ: dict[str, str]) -> list[Backend]:
    """Build a backend for every integration the user has connected."""
    backends: list[Backend] = []
    for app, credentials in mcp_config.credentials_from_env(environ).items():
        spec = mcp_config.server_spec(app)
        if spec is None:
            continue
        if spec.get("transport") == "stdio":
            env_map = spec.get("env_map") or {}
            backends.append(Backend(
                app=app,
                command=str(spec["command"]),
                args=[str(arg) for arg in spec["args"]],  # type: ignore[union-attr]
                env={env_key: credentials.get(field_name, "") for field_name, env_key in env_map.items()},  # type: ignore[union-attr]
            ))
        elif spec.get("transport") == "remote":
            credential_field = spec.get("auth_header_credential_field")
            headers = {}
            if isinstance(credential_field, str) and credentials.get(credential_field):
                headers["Authorization"] = f"Bearer {credentials[credential_field]}"
            backends.append(Backend(app=app, url=str(spec["url"]), headers=headers))
    return backends


class BackendPool:
    """Keeps one live MCP client session per connected app for the gateway's lifetime."""

    def __init__(self, backends: list[Backend]):
        self.backends = backends
        self.sessions: dict[str, ClientSession] = {}
        self.tools: dict[str, list[types.Tool]] = {}
        self.errors: dict[str, str] = {}
        self._stop = anyio.Event()

    async def start(self, task_group: anyio.abc.TaskGroup) -> None:
        ready = {backend.app: anyio.Event() for backend in self.backends}
        for backend in self.backends:
            task_group.start_soon(self._run, backend, ready[backend.app])
        for event in ready.values():
            await event.wait()

    def stop(self) -> None:
        self._stop.set()

    async def _run(self, backend: Backend, ready: anyio.Event) -> None:
        try:
            async with AsyncExitStack() as stack:
                # The transports open their own task groups, so they must be entered
                # outside the timeout's cancel scope; only the handshake is timed.
                if backend.url:
                    read, write, _ = await stack.enter_async_context(
                        streamablehttp_client(backend.url, headers=backend.headers)
                    )
                else:
                    params = StdioServerParameters(command=backend.command or "", args=backend.args, env=backend.env)
                    read, write = await stack.enter_async_context(stdio_client(params, errlog=sys.stderr))
                session = await stack.enter_async_context(ClientSession(read, write))
                with anyio.fail_after(BACKEND_START_TIMEOUT):
                    await session.initialize()
                    listed = await session.list_tools()
                self.sessions[backend.app] = session
                self.tools[backend.app] = list(listed.tools)
                logger.info("connected %s (%d tools)", backend.app, len(listed.tools))
                ready.set()
                await self._stop.wait()
        except Exception as exc:  # one broken app must not take the gateway down
            while isinstance(exc, BaseExceptionGroup) and len(exc.exceptions) == 1:
                exc = exc.exceptions[0]  # surface the real cause, not the task-group wrapper
            self.errors[backend.app] = str(exc) or type(exc).__name__
            logger.warning("could not start %s: %s", backend.app, self.errors[backend.app])
        finally:
            self.sessions.pop(backend.app, None)
            ready.set()


# ── approvals ─────────────────────────────────────────────────────────────────

def _applescript_string(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def desktop_approver(agent: str, app: str, tool: str, arguments: dict[str, Any]) -> bool:
    """Ask the user with a native macOS dialog. Anything but an explicit Allow denies."""
    if sys.platform != "darwin":
        return False
    details = json.dumps(arguments, ensure_ascii=False, default=str)
    if len(details) > 400:
        details = details[:399] + "…"
    message = f"{agent} wants to use {APP_LABELS.get(app, app)}: {tool}\n\n{details}"
    script = (
        f"display dialog {_applescript_string(message)} "
        'with title "BrainSquared" buttons {"Deny", "Allow"} default button "Deny" '
        "giving up after 120"
    )
    try:
        result = subprocess.run(["/usr/bin/osascript", "-e", script], capture_output=True, text=True, timeout=130)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "button returned:Allow" in result.stdout and "gave up:true" not in result.stdout


# ── the gateway ───────────────────────────────────────────────────────────────

def _error(text: str) -> types.CallToolResult:
    return types.CallToolResult(content=[types.TextContent(type="text", text=text)], isError=True)


class Gateway:
    def __init__(
        self,
        *,
        system_dir: Path,
        vault_root: Path,
        pool: BackendPool,
        approver: Approver = desktop_approver,
    ):
        self.policy_file = policy.policy_path(system_dir)
        self.audit_file = policy.audit_path(system_dir)
        self.vault_root = vault_root
        self.pool = pool
        self.approver = approver

    # Rules are re-read on every request so edits and revocations apply at once.
    def agent_for_token(self, token: str) -> policy.AgentPolicy | None:
        return policy.find_by_token(policy.load_policies(self.policy_file), token)

    def list_tools(self, agent: policy.AgentPolicy) -> list[types.Tool]:
        if agent.revoked:
            return []
        tools: list[types.Tool] = []
        for app, app_tools in self.pool.tools.items():
            if app not in self.pool.sessions:
                continue
            for tool in app_tools:
                decision = policy.decide(agent, app, tool.name)
                if not decision.allowed:
                    continue
                label = APP_LABELS.get(app, app)
                note = " (asks the user before running)" if decision.needs_approval else ""
                tools.append(tool.model_copy(update={
                    "name": f"{app}{TOOL_SEP}{tool.name}",
                    "description": f"[{label} via BrainSquared{note}] {tool.description or ''}".strip(),
                }))
        if policy.decide(agent, policy.CONTEXT_APP, CONTEXT_TOOL).allowed:
            tools.append(types.Tool(
                name=CONTEXT_TOOL,
                description=(
                    "Search the user's personal knowledge base (their BrainSquared vault) for context about "
                    "people, projects, commitments and preferences. Returns the most relevant notes."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "What you need context about"},
                        "limit": {"type": "integer", "description": "Max notes to return", "default": 5},
                    },
                    "required": ["query"],
                },
            ))
        return tools

    async def call_tool(self, agent: policy.AgentPolicy, name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        if name == CONTEXT_TOOL:
            app, tool = policy.CONTEXT_APP, CONTEXT_TOOL
        else:
            app, _, tool = name.partition(TOOL_SEP)

        decision = policy.decide(agent, app, tool)
        if not decision.allowed:
            self._audit(agent, app, tool, "denied", decision.reason, arguments)
            return _error(
                f"BrainSquared blocked this call: {decision.reason}. "
                "The user controls which apps each agent can use in BrainSquared → Agents."
            )

        if decision.needs_approval:
            approved = await anyio.to_thread.run_sync(self.approver, agent.name, app, tool, arguments)
            if not approved:
                self._audit(agent, app, tool, "rejected", "user did not approve", arguments)
                return _error("The user did not approve this action.")

        outcome = "approved" if decision.needs_approval else "allowed"
        if app == policy.CONTEXT_APP:
            self._audit(agent, app, tool, outcome, "", arguments)
            return self._context(agent, str(arguments.get("query", "")), int(arguments.get("limit", 5) or 5))

        session = self.pool.sessions.get(app)
        if session is None:
            reason = self.pool.errors.get(app, f"{app} is not connected")
            self._audit(agent, app, tool, "error", reason, arguments)
            return _error(f"{APP_LABELS.get(app, app)} is unavailable: {reason}")

        try:
            result = await session.call_tool(tool, arguments)
        except Exception as exc:
            self._audit(agent, app, tool, "error", str(exc), arguments)
            return _error(f"{APP_LABELS.get(app, app)} failed: {exc}")
        if result.isError:
            # Access was granted, but the app itself failed (expired login, bad input, ...).
            message = next((block.text for block in result.content if isinstance(block, types.TextContent)), "")
            self._audit(agent, app, tool, "error", message[:200], arguments)
        else:
            self._audit(agent, app, tool, outcome, "", arguments)
        return result

    def _context(self, agent: policy.AgentPolicy, query: str, limit: int) -> types.CallToolResult:
        terms = [term for term in query.lower().split() if len(term) > 2]
        scored = []
        for folder in agent.context:
            folder_path = (self.vault_root / folder).resolve()
            if not folder_path.is_relative_to(self.vault_root.resolve()):
                continue  # never let a rule reach outside the vault
            for note in read_vault(folder_path):
                title, body = note.title.lower(), note.content.lower()
                score = sum(title.count(term) * 3 + body.count(term) for term in terms)
                if score or not terms:
                    scored.append((score, folder, note))
        scored.sort(key=lambda item: item[0], reverse=True)
        if not scored:
            return types.CallToolResult(content=[types.TextContent(type="text", text="No matching notes.")])
        parts = []
        for _, folder, note in scored[: max(1, min(limit, 20))]:
            body = note.content.strip()
            if len(body) > 1500:
                body = body[:1500] + "…"
            parts.append(f"## {note.title}\n_{folder}/{note.relative_path}_\n\n{body}")
        return types.CallToolResult(content=[types.TextContent(type="text", text="\n\n---\n\n".join(parts))])

    def _audit(self, agent: policy.AgentPolicy, app: str, tool: str, outcome: str, reason: str, arguments: dict[str, Any]) -> None:
        policy.append_audit(
            self.audit_file, agent=agent.name, app=app, tool=tool,
            outcome=outcome, reason=reason, arguments=arguments,
        )


# ── HTTP app ──────────────────────────────────────────────────────────────────

def _token_from_request(request: Request) -> str:
    token = request.path_params.get("token", "")
    if not token:
        auth = request.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            token = auth[7:].strip()
    return token


def create_gateway_app(gateway: Gateway) -> Starlette:
    server: Server = Server("brainsquared")

    def current_agent() -> policy.AgentPolicy:
        request = server.request_context.request
        agent = gateway.agent_for_token(_token_from_request(request)) if request is not None else None
        if agent is None:
            raise PermissionError("Unknown BrainSquared agent token.")
        return agent

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return gateway.list_tools(current_agent())

    @server.call_tool(validate_input=False)
    async def _call_tool(name: str, arguments: dict[str, Any]) -> types.CallToolResult:
        return await gateway.call_tool(current_agent(), name, arguments or {})

    # Stateless: every request is handled on its own, so each one is checked
    # against the latest rules and identified by its own token.
    manager = StreamableHTTPSessionManager(app=server, stateless=True, json_response=True)

    class MCPEndpoint:
        async def __call__(self, scope, receive, send) -> None:
            request = Request(scope)
            if gateway.agent_for_token(_token_from_request(request)) is None:
                await JSONResponse({"error": "unknown agent token"}, status_code=401)(scope, receive, send)
                return
            await manager.handle_request(scope, receive, send)

    async def health(_request: Request) -> Response:
        return JSONResponse({
            "ok": True,
            "apps": sorted(gateway.pool.sessions),
            "errors": gateway.pool.errors,
        })

    @asynccontextmanager
    async def lifespan(_app: Starlette):
        async with anyio.create_task_group() as task_group:
            async with manager.run():
                await gateway.pool.start(task_group)
                try:
                    yield
                finally:
                    gateway.pool.stop()

    endpoint = MCPEndpoint()
    return Starlette(
        routes=[
            Route("/health", health),
            Route("/a/{token}/mcp", endpoint, methods=["GET", "POST", "DELETE"]),
            Route("/mcp", endpoint, methods=["GET", "POST", "DELETE"]),
        ],
        lifespan=lifespan,
    )


def gateway_url(token: str, *, host: str = "127.0.0.1", port: int = DEFAULT_GATEWAY_PORT) -> str:
    return f"http://{host}:{port}/a/{token}/mcp"


def run_gateway(*, system_dir: Path, vault_root: Path, environ: dict[str, str] | None = None, port: int = DEFAULT_GATEWAY_PORT) -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    backends = backends_from_env(dict(os.environ if environ is None else environ))
    gateway = Gateway(system_dir=system_dir, vault_root=vault_root, pool=BackendPool(backends))
    print(f"BrainSquared gateway on http://127.0.0.1:{port}")
    print(f"Apps: {', '.join(b.app for b in backends) or 'none connected yet'}")
    # Loopback only: the gateway holds the user's logins.
    uvicorn.run(create_gateway_app(gateway), host="127.0.0.1", port=port, log_level="warning")
