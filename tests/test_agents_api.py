import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from brain import policy
from brain.app_config import default_app_config
from brain.env_config import load_env_config
from brain.server import AppRuntime, create_app
from brain.session import SessionManager


def _client(tmp_path):
    app_cfg = default_app_config(tmp_path / "vault")
    runtime = AppRuntime(app_cfg=app_cfg, env_cfg=load_env_config(), session_manager=SessionManager(app_cfg.agent))
    return TestClient(create_app(runtime)), tmp_path / "vault" / "system"


def test_create_edit_revoke_and_audit(tmp_path):
    client, system = _client(tmp_path)

    created = client.post("/api/agents", json={"name": "instinct", "apps": {"google": "read"}, "create": True}).json()
    assert created["url"].endswith("/mcp") and created["apps"] == {"google": "read"}
    assert client.post("/api/agents", json={"name": "instinct", "create": True}).status_code == 409

    edited = client.post("/api/agents", json={"name": "instinct", "apps": {"google": "ask", "bad": "admin"}, "context": ["core"]}).json()
    assert edited["apps"] == {"google": "ask"} and edited["context"] == ["core"]
    assert edited["url"] == created["url"]

    assert client.post("/api/agents/instinct/revoke").json()["revoked"] is True
    assert client.post("/api/agents/nobody/revoke").status_code == 404

    listing = client.get("/api/agents").json()
    assert [a["name"] for a in listing["agents"]] == ["instinct"]
    assert listing["gateway"]["running"] in (True, False)

    policy.append_audit(policy.audit_path(system), agent="instinct", app="google", tool="list_emails", outcome="denied")
    entries = client.get("/api/agents/audit").json()["entries"]
    assert entries[0]["tool"] == "list_emails"
