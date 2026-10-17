"""Per-agent access rules and the audit log for the BrainSquared gateway.

Rules live in the vault at `system/access.yaml` so the user can read and edit
them directly. Each agent gets its own token and, per connected app, one of
three levels:

    read   — the agent may call read-only tools (list, get, search, ...)
    ask    — reads are allowed; every write pops a desktop approval prompt
    write  — reads and writes are allowed

Every tool call the gateway sees — allowed, denied or approved — is appended
to `system/audit.jsonl`.
"""

from __future__ import annotations

import hmac
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml

LEVELS = ("read", "ask", "write")
CONTEXT_APP = "vault"

_HEADER = """\
# BrainSquared access rules — which agent can reach which app.
#
# apps:     app -> read | ask | write
#           read  = read-only tools; ask = writes need your approval; write = full access
# context:  vault folders this agent may read through the get_context tool
# revoked:  true blocks every call from this agent immediately
#
# Tokens are secrets: anyone with an agent's URL can act as that agent.
"""

# Verbs that change something. Checked before the read verbs so that names like
# "create_and_list" are treated as writes.
_WRITE_VERBS = {
    "send", "create", "update", "delete", "remove", "post", "patch", "put", "add",
    "archive", "reply", "draft", "move", "comment", "merge", "close", "assign",
    "invite", "upload", "write", "edit", "set", "modify", "star", "label", "mark",
    "react", "fork", "push", "cancel", "accept", "decline", "rsvp", "trash",
    "approve", "publish", "schedule", "pay", "transfer", "book", "submit", "rename",
}
_READ_VERBS = {
    "get", "list", "search", "read", "fetch", "query", "find", "retrieve",
    "describe", "view", "show", "count", "lookup", "check", "status",
}
# Tools whose names contain a write verb but only read (Notion searches via POST).
_READ_OVERRIDES = {"API-post-search", "API-post-database-query", "API-query-data-source"}


@dataclass
class AgentPolicy:
    name: str
    token: str
    apps: dict[str, str] = field(default_factory=dict)
    context: list[str] = field(default_factory=list)
    revoked: bool = False


@dataclass(frozen=True)
class Decision:
    allowed: bool
    needs_approval: bool = False
    reason: str = ""


def policy_path(system_dir: Path) -> Path:
    return system_dir / "access.yaml"


def audit_path(system_dir: Path) -> Path:
    return system_dir / "audit.jsonl"


# ── rules file ────────────────────────────────────────────────────────────────

def load_policies(path: Path) -> dict[str, AgentPolicy]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    policies: dict[str, AgentPolicy] = {}
    for name, raw in (data.get("agents") or {}).items():
        raw = raw or {}
        apps = {str(app): str(level) for app, level in (raw.get("apps") or {}).items() if level in LEVELS}
        policies[str(name)] = AgentPolicy(
            name=str(name),
            token=str(raw.get("token") or ""),
            apps=apps,
            context=[str(folder) for folder in (raw.get("context") or [])],
            revoked=bool(raw.get("revoked", False)),
        )
    return policies


def save_policies(path: Path, policies: dict[str, AgentPolicy]) -> None:
    data = {
        "agents": {
            policy.name: {
                "token": policy.token,
                "apps": dict(policy.apps),
                "context": list(policy.context),
                "revoked": policy.revoked,
            }
            for policy in policies.values()
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_HEADER + "\n" + yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    path.chmod(0o600)


def parse_apps(spec: str) -> dict[str, str]:
    """Parse "google:read,notion:write" into {"google": "read", "notion": "write"}."""
    apps: dict[str, str] = {}
    for item in filter(None, (part.strip() for part in spec.split(","))):
        app, _, level = item.partition(":")
        level = level or "read"
        if level not in LEVELS:
            raise ValueError(f"Unknown access level {level!r} for {app} — use one of {', '.join(LEVELS)}.")
        apps[app.strip()] = level
    return apps


def upsert_agent(
    path: Path,
    name: str,
    *,
    apps: dict[str, str] | None = None,
    context: Iterable[str] | None = None,
) -> AgentPolicy:
    """Create an agent (with a fresh token) or update an existing one's access."""
    policies = load_policies(path)
    policy = policies.get(name) or AgentPolicy(name=name, token=secrets.token_urlsafe(24))
    if apps is not None:
        policy.apps = dict(apps)
    if context is not None:
        policy.context = list(context)
    policies[name] = policy
    save_policies(path, policies)
    return policy


def set_revoked(path: Path, name: str, revoked: bool) -> AgentPolicy:
    policies = load_policies(path)
    if name not in policies:
        raise KeyError(f"No agent named {name!r}.")
    policies[name].revoked = revoked
    save_policies(path, policies)
    return policies[name]


def remove_agent(path: Path, name: str) -> None:
    policies = load_policies(path)
    if policies.pop(name, None) is None:
        raise KeyError(f"No agent named {name!r}.")
    save_policies(path, policies)


def find_by_token(policies: dict[str, AgentPolicy], token: str) -> AgentPolicy | None:
    if not token:
        return None
    for policy in policies.values():
        if policy.token and hmac.compare_digest(policy.token, token):
            return policy
    return None


# ── decisions ─────────────────────────────────────────────────────────────────

def _name_tokens(tool_name: str) -> list[str]:
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", tool_name)
    return [token for token in re.split(r"[^A-Za-z0-9]+", spaced.lower()) if token]


def classify_tool(tool_name: str) -> str:
    """Return "read" or "write". Unknown tools count as writes (fail closed)."""
    if tool_name in _READ_OVERRIDES:
        return "read"
    tokens = _name_tokens(tool_name)
    if any(token in _WRITE_VERBS for token in tokens):
        return "write"
    if any(token in _READ_VERBS for token in tokens):
        return "read"
    return "write"


def decide(policy: AgentPolicy, app: str, tool_name: str) -> Decision:
    if policy.revoked:
        return Decision(False, reason="access revoked")
    if app == CONTEXT_APP:
        if policy.context:
            return Decision(True)
        return Decision(False, reason="no vault context granted")
    level = policy.apps.get(app)
    if level is None:
        return Decision(False, reason=f"no access to {app}")
    if classify_tool(tool_name) == "read":
        return Decision(True)
    if level == "write":
        return Decision(True)
    if level == "ask":
        return Decision(True, needs_approval=True)
    return Decision(False, reason=f"read-only access to {app}")


# ── audit log ─────────────────────────────────────────────────────────────────

def _preview(arguments: dict[str, Any] | None, limit: int = 240) -> str:
    if not arguments:
        return ""
    text = json.dumps(arguments, ensure_ascii=False, default=str)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def append_audit(
    path: Path,
    *,
    agent: str,
    app: str,
    tool: str,
    outcome: str,
    reason: str = "",
    arguments: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "agent": agent,
        "app": app,
        "tool": tool,
        "outcome": outcome,
        "reason": reason,
        "args": _preview(arguments),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def read_audit(path: Path, *, limit: int = 100, agent: str | None = None) -> list[dict[str, Any]]:
    """Return the newest `limit` entries, newest first."""
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if agent is None or entry.get("agent") == agent:
            entries.append(entry)
    return list(reversed(entries[-limit:]))
