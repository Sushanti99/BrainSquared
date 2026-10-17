import pytest

from brain import policy


@pytest.mark.parametrize("name,kind", [
    ("list_emails", "read"),
    ("get_todays_events", "read"),
    ("search_emails", "read"),
    ("API-get-block-children", "read"),
    ("API-post-search", "read"),          # Notion searches with POST
    ("send_email", "write"),
    ("slack_post_message", "write"),
    ("API-patch-page", "write"),
    ("createIssue", "write"),
    ("list_and_delete", "write"),         # any write verb wins
    ("frobnicate", "write"),              # unknown tools fail closed
])
def test_classify_tool(name, kind):
    assert policy.classify_tool(name) == kind


def test_decide_follows_levels():
    agent = policy.AgentPolicy(name="a", token="t", apps={"google": "read", "notion": "ask", "slack": "write"})

    assert policy.decide(agent, "google", "list_emails").allowed
    assert policy.decide(agent, "google", "send_email") == policy.Decision(False, reason="read-only access to google")
    assert policy.decide(agent, "notion", "API-patch-page") == policy.Decision(True, needs_approval=True)
    assert policy.decide(agent, "notion", "API-get-self") == policy.Decision(True)
    assert policy.decide(agent, "slack", "slack_post_message") == policy.Decision(True)
    assert policy.decide(agent, "github", "list_issues") == policy.Decision(False, reason="no access to github")
    assert not policy.decide(agent, policy.CONTEXT_APP, "get_context").allowed

    agent.revoked = True
    assert policy.decide(agent, "google", "list_emails") == policy.Decision(False, reason="access revoked")


def test_rules_file_round_trip(tmp_path):
    rules = tmp_path / "system" / "access.yaml"

    created = policy.upsert_agent(rules, "codex", apps={"notion": "write"}, context=["core"])
    updated = policy.upsert_agent(rules, "codex", apps={"notion": "read"})

    assert updated.token == created.token  # changing access keeps the agent's URL
    loaded = policy.load_policies(rules)["codex"]
    assert loaded.apps == {"notion": "read"} and loaded.context == ["core"]
    assert rules.read_text().startswith("# BrainSquared access rules")
    assert oct(rules.stat().st_mode & 0o777) == "0o600"

    policy.set_revoked(rules, "codex", True)
    assert policy.find_by_token(policy.load_policies(rules), created.token).revoked
    assert policy.find_by_token(policy.load_policies(rules), "wrong") is None

    policy.remove_agent(rules, "codex")
    assert policy.load_policies(rules) == {}
    with pytest.raises(KeyError):
        policy.set_revoked(rules, "codex", False)


def test_parse_apps():
    assert policy.parse_apps("google:read, notion:write,slack") == {"google": "read", "notion": "write", "slack": "read"}
    with pytest.raises(ValueError):
        policy.parse_apps("google:admin")


def test_audit_log_is_newest_first_and_filterable(tmp_path):
    log = tmp_path / "audit.jsonl"
    policy.append_audit(log, agent="a", app="google", tool="list_emails", outcome="allowed", arguments={"days": 1})
    policy.append_audit(log, agent="b", app="slack", tool="post", outcome="denied", reason="no access to slack",
                        arguments={"text": "x" * 1000})

    entries = policy.read_audit(log)
    assert [e["agent"] for e in entries] == ["b", "a"]
    assert len(entries[0]["args"]) == 240
    assert [e["agent"] for e in policy.read_audit(log, agent="a")] == ["a"]
