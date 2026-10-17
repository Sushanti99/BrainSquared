"""Manage MCP server configurations for Claude Code and Codex."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable, Mapping

# Claude Code reads user-scope MCP servers from ~/.claude.json's top-level
# "mcpServers" key (verified via `claude mcp add`/`claude mcp list`) — not from
# ~/.claude/settings.json, which the CLI silently ignores for this purpose.
CLAUDE_CONFIG = Path.home() / ".claude.json"
CODEX_CONFIG = Path.home() / ".codex" / "config.toml"

def _stdio_server(command: str, args: list[str], env_map: Mapping[str, str]) -> dict[str, object]:
    return {
        "transport": "stdio",
        "command": command,
        "args": list(args),
        "env_map": dict(env_map),
    }


def _remote_server(
    url: str,
    *,
    bearer_token_env_var: str | None = None,
    features: Mapping[str, bool] | None = None,
) -> dict[str, object]:
    data: dict[str, object] = {"transport": "remote", "url": url}
    if bearer_token_env_var:
        data["bearer_token_env_var"] = bearer_token_env_var
    if features:
        data["features"] = dict(features)
    return data


def _http_remote_server(url: str, *, auth_header_credential_field: str) -> dict[str, object]:
    """A remote MCP server for Claude Code, authenticated via a literal Bearer header."""
    return {
        "transport": "remote",
        "url": url,
        "auth_header_credential_field": auth_header_credential_field,
    }


# Path to the built-in Google MCP server script.
_GOOGLE_MCP_SERVER = str(Path(__file__).parent / "mcp_google_server.py")


def _find_python_with_mcp() -> str:
    """Return the Python executable that has the mcp package installed."""
    candidates = [
        shutil.which("python3"),
        shutil.which("python"),
        sys.executable,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            result = subprocess.run(
                [candidate, "-c", "import mcp"],
                capture_output=True, timeout=5,
            )
            if result.returncode == 0:
                return candidate
        except Exception:
            continue
    # Fallback — will fail at runtime with a clear error from the MCP server
    return sys.executable


# MCP server definitions per backend.
_SERVERS: dict[str, dict[str, dict[str, object]]] = {
    "google": {
        "claude-code": _stdio_server(
            _find_python_with_mcp(),
            [_GOOGLE_MCP_SERVER],
            {
                "credentials_file": "GOOGLE_CREDENTIALS_FILE",
                "token_file": "GOOGLE_TOKEN_FILE",
            },
        ),
        "codex": _stdio_server(
            _find_python_with_mcp(),
            [_GOOGLE_MCP_SERVER],
            {
                "credentials_file": "GOOGLE_CREDENTIALS_FILE",
                "token_file": "GOOGLE_TOKEN_FILE",
            },
        ),
    },
    "github": {
        "claude-code": _stdio_server(
            "npx",
            ["-y", "@modelcontextprotocol/server-github"],
            {"api_key": "GITHUB_PERSONAL_ACCESS_TOKEN"},
        ),
        "codex": _stdio_server(
            "npx",
            ["-y", "@modelcontextprotocol/server-github"],
            {"api_key": "GITHUB_PERSONAL_ACCESS_TOKEN"},
        ),
    },
    "notion": {
        "claude-code": _stdio_server(
            "npx",
            ["-y", "@notionhq/notion-mcp-server"],
            {"api_key": "NOTION_API_KEY"},
        ),
        "codex": _stdio_server(
            "npx",
            ["-y", "@notionhq/notion-mcp-server"],
            {"api_key": "NOTION_API_KEY"},
        ),
    },
    "linear": {
        # Linear's MCP is a hosted remote endpoint, not an npm package — there is
        # no "@linear/mcp" package. Claude Code needs a literal "Authorization:
        # Bearer <token>" header (unlike Codex, which references an env var name).
        "claude-code": _http_remote_server(
            "https://mcp.linear.app/mcp",
            auth_header_credential_field="api_key",
        ),
        "codex": _remote_server(
            "https://mcp.linear.app/mcp",
            bearer_token_env_var="LINEAR_API_KEY",
            features={"experimental_use_rmcp_client": True},
        ),
    },
    "slack": {
        "claude-code": _stdio_server(
            "npx",
            ["-y", "@modelcontextprotocol/server-slack"],
            {"bot_token": "SLACK_BOT_TOKEN", "team_id": "SLACK_TEAM_ID"},
        ),
        "codex": _stdio_server(
            "npx",
            ["-y", "@modelcontextprotocol/server-slack"],
            {"bot_token": "SLACK_BOT_TOKEN", "team_id": "SLACK_TEAM_ID"},
        ),
    },
}


def _normalize_agents(agents: Iterable[str] | str | None) -> list[str]:
    if agents is None:
        return ["claude-code", "codex"]
    if isinstance(agents, str):
        return [agents]
    return list(agents)


def _server_spec(integration_id: str, agent: str) -> dict[str, object] | None:
    return _SERVERS.get(integration_id, {}).get(agent)


def _read_claude_settings() -> dict:
    if not CLAUDE_CONFIG.exists():
        return {}
    try:
        return json.loads(CLAUDE_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_claude_settings(settings: dict) -> None:
    CLAUDE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CLAUDE_CONFIG.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def _read_codex_config() -> str:
    if not CODEX_CONFIG.exists():
        return ""
    return CODEX_CONFIG.read_text(encoding="utf-8")


def _write_codex_config(text: str) -> None:
    CODEX_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CODEX_CONFIG.write_text(text, encoding="utf-8")


def _toml_string(value: str) -> str:
    return json.dumps(value)


def _codex_server_pattern(integration_id: str) -> re.Pattern[str]:
    escaped_id = re.escape(integration_id)
    return re.compile(
        rf"(?ms)^\[mcp_servers\.{escaped_id}\]\n.*?(?=^\[(?!mcp_servers\.{escaped_id}(?:[.\]])).*$|\Z)"
    )


_FEATURES_BLOCK_PATTERN = re.compile(r"(?ms)^\[features\]\n.*?(?=^\[|\Z)")


def _replace_or_append_block(text: str, pattern: re.Pattern[str], block: str) -> str:
    normalized_block = block.strip()
    if pattern.search(text):
        updated = pattern.sub(normalized_block + "\n\n", text, count=1)
    else:
        prefix = text.rstrip()
        updated = f"{prefix}\n\n{normalized_block}\n" if prefix else f"{normalized_block}\n"
    return updated.rstrip() + "\n"


def _build_feature_block(features: Mapping[str, bool]) -> str:
    lines = ["[features]"]
    for key, value in sorted(features.items()):
        lines.append(f"{key} = {'true' if value else 'false'}")
    return "\n".join(lines)


def _merge_codex_features(text: str, features: Mapping[str, bool]) -> str:
    if not features:
        return text

    existing: dict[str, str] = {}
    match = _FEATURES_BLOCK_PATTERN.search(text)
    if match:
        for raw_line in match.group(0).splitlines()[1:]:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            existing[key.strip()] = value.strip()

    for key, value in features.items():
        existing[key] = "true" if value else "false"

    return _replace_or_append_block(text, _FEATURES_BLOCK_PATTERN, _build_feature_block(existing))


def _build_env(server_spec: Mapping[str, object], credentials: Mapping[str, str]) -> dict[str, str]:
    env_map = server_spec.get("env_map")
    if not isinstance(env_map, Mapping):
        return {}
    return {env_key: credentials.get(field, "") for field, env_key in env_map.items()}


def _claude_server_entry(server_spec: Mapping[str, object], credentials: Mapping[str, str]) -> dict[str, object] | None:
    transport = server_spec.get("transport")
    if transport == "stdio":
        return {
            "command": server_spec["command"],
            "args": server_spec["args"],
            "env": _build_env(server_spec, credentials),
        }
    if transport == "remote":
        entry: dict[str, object] = {"type": "http", "url": server_spec["url"]}
        credential_field = server_spec.get("auth_header_credential_field")
        if isinstance(credential_field, str) and credential_field:
            token = credentials.get(credential_field, "")
            entry["headers"] = {"Authorization": f"Bearer {token}"}
        return entry
    return None


def _add_claude_server(integration_id: str, credentials: Mapping[str, str]) -> None:
    server_spec = _server_spec(integration_id, "claude-code")
    if server_spec is None:
        return
    entry = _claude_server_entry(server_spec, credentials)
    if entry is None:
        return
    settings = _read_claude_settings()
    settings.setdefault("mcpServers", {})[integration_id] = entry
    _write_claude_settings(settings)


def _build_codex_server_block(integration_id: str, server_spec: Mapping[str, object], credentials: Mapping[str, str]) -> str:
    lines = [f"[mcp_servers.{integration_id}]"]
    transport = server_spec.get("transport")

    if transport == "stdio":
        args = ", ".join(_toml_string(arg) for arg in server_spec["args"])
        lines.append(f"command = {_toml_string(server_spec['command'])}")
        lines.append(f"args = [{args}]")
        env = _build_env(server_spec, credentials)
        if env:
            lines.append("")
            lines.append(f"[mcp_servers.{integration_id}.env]")
            for key, value in env.items():
                lines.append(f"{key} = {_toml_string(value)}")
        return "\n".join(lines)

    if transport == "remote":
        lines.append(f"url = {_toml_string(server_spec['url'])}")
        bearer_token_env_var = server_spec.get("bearer_token_env_var")
        if isinstance(bearer_token_env_var, str) and bearer_token_env_var:
            lines.append(f"bearer_token_env_var = {_toml_string(bearer_token_env_var)}")
        return "\n".join(lines)

    raise ValueError(f"Unsupported Codex MCP transport for {integration_id}: {transport}")


def _add_codex_server(integration_id: str, credentials: Mapping[str, str]) -> None:
    text = _read_codex_config()
    server_spec = _server_spec(integration_id, "codex")
    if server_spec is None:
        return

    updated = _replace_or_append_block(
        text,
        _codex_server_pattern(integration_id),
        _build_codex_server_block(integration_id, server_spec, credentials),
    )
    features = server_spec.get("features")
    if isinstance(features, Mapping):
        updated = _merge_codex_features(updated, {str(key): bool(value) for key, value in features.items()})
    _write_codex_config(updated)


def add_server(integration_id: str, credentials: dict[str, str], *, agents: Iterable[str] | str | None = None) -> None:
    """Write an MCP server entry for one or more agent backends.

    Backends routed through the BrainSquared gateway are skipped: giving them a
    direct server would let them bypass the gateway's access rules.
    """
    if integration_id not in _SERVERS:
        return
    for agent in _normalize_agents(agents):
        if gateway_enabled(agent):
            continue
        if agent == "claude-code":
            _add_claude_server(integration_id, credentials)
        elif agent == "codex":
            _add_codex_server(integration_id, credentials)


def _remove_claude_server(integration_id: str) -> None:
    settings = _read_claude_settings()
    settings.get("mcpServers", {}).pop(integration_id, None)
    _write_claude_settings(settings)


def _remove_codex_server(integration_id: str) -> None:
    text = _read_codex_config()
    updated = _codex_server_pattern(integration_id).sub("", text, count=1)
    updated = re.sub(r"\n{3,}", "\n\n", updated).strip()
    _write_codex_config(updated + ("\n" if updated else ""))


def remove_server(integration_id: str, *, agents: Iterable[str] | str | None = None) -> None:
    """Remove an MCP server entry for one or more agent backends."""
    for agent in _normalize_agents(agents):
        if agent == "claude-code":
            _remove_claude_server(integration_id)
        elif agent == "codex":
            _remove_codex_server(integration_id)


def _connected_claude_integrations() -> dict[str, bool]:
    mcp_servers = _read_claude_settings().get("mcpServers", {})
    connected: dict[str, bool] = {}
    for name, defs in _SERVERS.items():
        connected[name] = "claude-code" in defs and name in mcp_servers
    return connected


def _connected_codex_integrations() -> dict[str, bool]:
    config_text = _read_codex_config()
    connected: dict[str, bool] = {}
    for name, defs in _SERVERS.items():
        server_spec = defs.get("codex")
        if server_spec is None:
            connected[name] = False
            continue

        match = _codex_server_pattern(name).search(config_text)
        if match is None:
            connected[name] = False
            continue

        block = match.group(0)
        if server_spec.get("transport") == "stdio":
            args = ", ".join(_toml_string(arg) for arg in server_spec["args"])
            expected_lines = [
                f"command = {_toml_string(server_spec['command'])}",
                f"args = [{args}]",
            ]
            env_map = server_spec.get("env_map")
            if isinstance(env_map, Mapping):
                expected_lines.extend(f"{env_var} =" for env_var in env_map.values())
            connected[name] = all(line in block for line in expected_lines)
            continue

        if server_spec.get("transport") == "remote":
            expected_lines = [f"url = {_toml_string(server_spec['url'])}"]
            bearer_token_env_var = server_spec.get("bearer_token_env_var")
            if isinstance(bearer_token_env_var, str) and bearer_token_env_var:
                expected_lines.append(f"bearer_token_env_var = {_toml_string(bearer_token_env_var)}")
            connected[name] = all(line in block for line in expected_lines)
            continue

        connected[name] = False
    return connected


def connected_integrations(agent: str | None = None) -> dict[str, bool]:
    """Return which MCP-backed integrations are configured for the requested agent."""
    if agent == "claude-code":
        return _connected_claude_integrations()
    if agent == "codex":
        return _connected_codex_integrations()

    combined = {name: False for name in _SERVERS}
    for backend_status in (_connected_claude_integrations(), _connected_codex_integrations()):
        for name, enabled in backend_status.items():
            combined[name] = combined[name] or enabled
    return combined


def credentials_from_env(environ: Mapping[str, str] | None = None) -> dict[str, dict[str, str]]:
    """Return MCP credentials for every integration that is connected in the env."""
    env = os.environ if environ is None else environ
    mappings = {
        "github": {"api_key": env.get("GITHUB_TOKEN", "")},
        "notion": {"api_key": env.get("NOTION_API_KEY", "")},
        "linear": {"api_key": env.get("LINEAR_API_KEY", "")},
        "slack": {
            "bot_token": env.get("SLACK_BOT_TOKEN", ""),
            "team_id": env.get("SLACK_TEAM_ID", ""),
        },
    }
    connected = {
        integration_id: credentials
        for integration_id, credentials in mappings.items()
        if any(value for value in credentials.values())
    }

    # Google: activate if token.json exists (OAuth already done via UI)
    token_file = env.get("GOOGLE_TOKEN_FILE", "")
    if token_file and Path(token_file).exists():
        connected["google"] = {
            "credentials_file": env.get("GOOGLE_CREDENTIALS_FILE", ""),
            "token_file": token_file,
        }
    return connected


def sync_from_env(agent: str | None = None, environ: Mapping[str, str] | None = None) -> None:
    """Mirror env-backed credentials into MCP config for the requested agent."""
    for integration_id, credentials in credentials_from_env(environ).items():
        add_server(integration_id, credentials, agents=agent)


def server_spec(integration_id: str) -> dict[str, object] | None:
    """The server definition the gateway uses to reach an integration itself."""
    return _server_spec(integration_id, "claude-code")


# ── BrainSquared gateway ──────────────────────────────────────────────────────
# When a backend is routed through the gateway, its config holds one MCP server
# ("brainsquared") pointing at the gateway, and no direct integration servers.

GATEWAY_SERVER_NAME = "brainsquared"


def gateway_enabled(agent: str) -> bool:
    if agent == "claude-code":
        return GATEWAY_SERVER_NAME in _read_claude_settings().get("mcpServers", {})
    if agent == "codex":
        return _codex_server_pattern(GATEWAY_SERVER_NAME).search(_read_codex_config()) is not None
    return False


def add_gateway(url: str, *, agents: Iterable[str] | str | None = None) -> None:
    """Point the given backends at the gateway and drop their direct servers."""
    for agent in _normalize_agents(agents):
        if agent == "claude-code":
            settings = _read_claude_settings()
            servers = settings.setdefault("mcpServers", {})
            for integration_id in _SERVERS:
                servers.pop(integration_id, None)
            servers[GATEWAY_SERVER_NAME] = {"type": "http", "url": url}
            _write_claude_settings(settings)
        elif agent == "codex":
            for integration_id in _SERVERS:
                _remove_codex_server(integration_id)
            text = _replace_or_append_block(
                _read_codex_config(),
                _codex_server_pattern(GATEWAY_SERVER_NAME),
                f"[mcp_servers.{GATEWAY_SERVER_NAME}]\nurl = {_toml_string(url)}",
            )
            _write_codex_config(_merge_codex_features(text, {"experimental_use_rmcp_client": True}))


def remove_gateway(*, agents: Iterable[str] | str | None = None, environ: Mapping[str, str] | None = None) -> None:
    """Stop routing the given backends through the gateway and restore direct servers."""
    for agent in _normalize_agents(agents):
        if agent == "claude-code":
            _remove_claude_server(GATEWAY_SERVER_NAME)
        elif agent == "codex":
            _remove_codex_server(GATEWAY_SERVER_NAME)
        sync_from_env(agent, environ)


def supported_integrations() -> list[str]:
    return list(_SERVERS.keys())
