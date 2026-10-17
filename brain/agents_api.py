"""Web routes for the Agents & Access tab: who can reach what, and what they did."""

from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse

from brain import gateway, mcp_config, policy
from brain.vault import resolve_vault_paths


async def _gateway_health() -> dict[str, object]:
    try:
        async with httpx.AsyncClient(timeout=0.5) as client:
            response = await client.get(f"http://127.0.0.1:{gateway.DEFAULT_GATEWAY_PORT}/health")
        return {"running": True, **response.json()}
    except (httpx.HTTPError, ValueError):
        return {"running": False, "apps": [], "errors": {}}


def _agent_payload(agent: policy.AgentPolicy) -> dict[str, object]:
    return {
        "name": agent.name,
        "apps": agent.apps,
        "context": agent.context,
        "revoked": agent.revoked,
        "url": gateway.gateway_url(agent.token),
    }


def register(app: FastAPI, runtime) -> None:
    def system_dir():
        return resolve_vault_paths(runtime.app_cfg).system

    @app.get("/api/agents")
    async def list_agents():
        agents = policy.load_policies(policy.policy_path(system_dir()))
        environ = {**os.environ, **runtime.env_cfg.raw_env}
        return {
            "agents": [_agent_payload(agent) for agent in agents.values()],
            "gateway": await _gateway_health(),
            "connected_apps": sorted(mcp_config.credentials_from_env(environ)),
            "app_labels": gateway.APP_LABELS,
        }

    @app.post("/api/agents")
    async def save_agent(body: dict):
        name = str(body.get("name", "")).strip()
        if not name:
            return JSONResponse({"error": "Give the agent a name."}, status_code=400)
        rules = policy.policy_path(system_dir())
        if body.get("create") and name in policy.load_policies(rules):
            return JSONResponse({"error": f"An agent named {name!r} already exists."}, status_code=409)
        apps = {str(app_id): str(level) for app_id, level in (body.get("apps") or {}).items() if level in policy.LEVELS}
        context = [str(folder) for folder in body.get("context") or []]
        agent = policy.upsert_agent(rules, name, apps=apps, context=context)
        return _agent_payload(agent)

    @app.post("/api/agents/{name}/revoke")
    async def revoke_agent(name: str):
        return _set_revoked(name, True)

    @app.post("/api/agents/{name}/restore")
    async def restore_agent(name: str):
        return _set_revoked(name, False)

    def _set_revoked(name: str, revoked: bool):
        try:
            agent = policy.set_revoked(policy.policy_path(system_dir()), name, revoked)
        except KeyError as exc:
            return JSONResponse({"error": str(exc)}, status_code=404)
        return _agent_payload(agent)

    @app.get("/api/agents/audit")
    async def audit(limit: int = Query(50, ge=1, le=500), agent: str | None = None):
        return {"entries": policy.read_audit(policy.audit_path(system_dir()), limit=limit, agent=agent)}
