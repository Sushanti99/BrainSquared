from brain.agent_backends import CodexBackend, parse_claude_stream_line, parse_codex_jsonl_line
from brain.app_config import default_app_config


def test_parse_claude_stream_line_extracts_text_chunk():
    event = parse_claude_stream_line('{"type":"content_block_delta","delta":{"text":"hello"}}')

    assert event is not None
    assert event.type == "chunk"
    assert event.content == "hello"


def test_parse_codex_jsonl_line_extracts_text_chunk():
    event = parse_codex_jsonl_line('{"type":"response.output_text.delta","delta":"world"}')

    assert event is not None
    assert event.type == "chunk"
    assert event.content == "world"


def test_codex_build_command_adds_skip_git_repo_check_for_non_repo(tmp_path, monkeypatch):
    app_cfg = default_app_config(tmp_path / "vault", "codex")
    backend = CodexBackend(app_cfg)
    monkeypatch.setattr("brain.agent_backends.path_is_git_repo", lambda path: False)

    command = backend.build_command("hello")

    assert "--skip-git-repo-check" in command


def test_codex_build_command_adds_workspace_write_when_missing(tmp_path, monkeypatch):
    app_cfg = default_app_config(tmp_path / "vault", "codex")
    app_cfg.agents["codex"].args = ["exec", "--json"]
    backend = CodexBackend(app_cfg)
    monkeypatch.setattr("brain.agent_backends.path_is_git_repo", lambda path: True)

    command = backend.build_command("hello")

    assert "--sandbox" in command
    sandbox_index = command.index("--sandbox")
    assert command[sandbox_index + 1] == "workspace-write"
