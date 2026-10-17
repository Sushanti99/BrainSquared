"""End-to-end tests: a real gateway over HTTP, in front of a fake app MCP server."""

import socket
import sys
import threading
import time
from contextlib import contextmanager
from pathlib import Path

import anyio
import httpx
import pytest
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from brain import gateway as gw
from brain import policy

FAKE_SERVER = Path(__file__).parent / "fixtures" / "fake_mcp_server.py"


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@contextmanager
def running_gateway(tmp_path, approver=lambda *args: False):
    vault = tmp_path / "vault"
    (vault / "core").mkdir(parents=True)
    (vault / "core" / "Taxes.md").write_text("# Taxes\nFile 2026 taxes with the CPA by April.\n")
    (vault / "thoughts").mkdir()
    (vault / "thoughts" / "Private.md").write_text("# Private\nTaxes journal entry, keep private.\n")
    system = vault / "system"
    system.mkdir()

    pool = gw.BackendPool([gw.Backend(app="fake", command=sys.executable, args=[str(FAKE_SERVER)])])
    gateway = gw.Gateway(system_dir=system, vault_root=vault, pool=pool, approver=approver)
    port = _free_port()
    server = uvicorn.Server(uvicorn.Config(gw.create_gateway_app(gateway), host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 30
    while not server.started:
        if time.time() > deadline:
            raise RuntimeError("gateway did not start")
        time.sleep(0.05)
    try:
        yield system, port
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def _session_call(url, fn):
    async def run():
        async with streamablehttp_client(url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await fn(session)
    return anyio.run(run)


def _tool_names(url):
    async def fn(session):
        return sorted(tool.name for tool in (await session.list_tools()).tools)
    return _session_call(url, fn)


def _call(url, name, arguments):
    async def fn(session):
        return await session.call_tool(name, arguments)
    return _session_call(url, fn)


def test_read_only_agent_sees_and_runs_only_read_tools(tmp_path):
    with running_gateway(tmp_path) as (system, port):
        agent = policy.upsert_agent(policy.policy_path(system), "claude-code", apps={"fake": "read"})
        url = gw.gateway_url(agent.token, port=port)

        assert _tool_names(url) == ["fake__get_expired", "fake__list_messages"]
        result = _call(url, "fake__list_messages", {"limit": 2})
        assert not result.isError
        assert "message 2" in result.content[0].text

        blocked = _call(url, "fake__send_message", {"to": "bob", "text": "hi"})
        assert blocked.isError
        assert "read-only access to fake" in blocked.content[0].text

        log = policy.read_audit(policy.audit_path(system))
        assert [(e["tool"], e["outcome"]) for e in log] == [("send_message", "denied"), ("list_messages", "allowed")]


def test_revoking_blocks_the_next_call(tmp_path):
    with running_gateway(tmp_path) as (system, port):
        rules = policy.policy_path(system)
        agent = policy.upsert_agent(rules, "codex", apps={"fake": "write"})
        url = gw.gateway_url(agent.token, port=port)
        assert not _call(url, "fake__send_message", {"to": "bob", "text": "hi"}).isError

        policy.set_revoked(rules, "codex", True)

        assert _tool_names(url) == []
        result = _call(url, "fake__list_messages", {})
        assert result.isError and "access revoked" in result.content[0].text


def test_ask_level_requires_user_approval(tmp_path):
    decisions = []

    def approver(agent, app, tool, arguments):
        decisions.append((agent, app, tool))
        return arguments.get("to") == "alice"

    with running_gateway(tmp_path, approver=approver) as (system, port):
        agent = policy.upsert_agent(policy.policy_path(system), "instinct", apps={"fake": "ask"})
        url = gw.gateway_url(agent.token, port=port)

        assert not _call(url, "fake__send_message", {"to": "alice", "text": "hi"}).isError
        assert _call(url, "fake__send_message", {"to": "bob", "text": "hi"}).isError
        assert not _call(url, "fake__list_messages", {}).isError  # reads never ask

        assert decisions == [("instinct", "fake", "send_message")] * 2
        outcomes = [e["outcome"] for e in policy.read_audit(policy.audit_path(system))]
        assert outcomes == ["allowed", "rejected", "approved"]


def test_context_tool_only_reads_granted_folders(tmp_path):
    with running_gateway(tmp_path) as (system, port):
        agent = policy.upsert_agent(policy.policy_path(system), "muse", apps={}, context=["core"])
        url = gw.gateway_url(agent.token, port=port)

        assert _tool_names(url) == ["get_context"]
        text = _call(url, "get_context", {"query": "taxes"}).content[0].text
        assert "CPA" in text
        assert "journal" not in text  # thoughts/ was not granted


def test_unknown_token_is_rejected(tmp_path):
    with running_gateway(tmp_path) as (_system, port):
        response = httpx.post(gw.gateway_url("not-a-token", port=port), json={})
        assert response.status_code == 401


def test_app_errors_are_logged_as_errors_not_allowed(tmp_path):
    with running_gateway(tmp_path) as (system, port):
        agent = policy.upsert_agent(policy.policy_path(system), "a", apps={"fake": "read"})
        result = _call(gw.gateway_url(agent.token, port=port), "fake__get_expired", {})

        assert result.isError
        entry = policy.read_audit(policy.audit_path(system))[0]
        assert entry["outcome"] == "error" and "invalid_grant" in entry["reason"]
