from pathlib import Path

import yaml

from brain.app_config import default_app_config, load_app_config, write_default_app_config
from brain.models import DEFAULT_SERVER_PORT


def test_default_app_config_uses_high_server_port(tmp_path):
    assert default_app_config(tmp_path / "vault").server.port == DEFAULT_SERVER_PORT


def test_load_app_config_from_vault_system_path(tmp_path):
    vault_path = tmp_path / "vault"
    config_path = vault_path / "system" / "brain.config.yaml"
    write_default_app_config(config_path, vault_path, agent="codex")

    app_cfg = load_app_config(vault_path=vault_path)

    assert app_cfg.agent == "codex"
    assert app_cfg.vault.path == vault_path.resolve()
    assert app_cfg.config_path == config_path.resolve()
    assert app_cfg.server.port == DEFAULT_SERVER_PORT


def test_load_app_config_applies_overrides(tmp_path):
    vault_path = tmp_path / "vault"
    config_path = vault_path / "system" / "brain.config.yaml"
    write_default_app_config(config_path, vault_path, agent="claude-code")

    app_cfg = load_app_config(vault_path=vault_path, agent_override="codex", port_override=4444)

    assert app_cfg.agent == "codex"
    assert app_cfg.server.port == 4444


def test_write_default_app_config_persists_folder_overrides(tmp_path):
    vault_path = tmp_path / "vault"
    config_path = vault_path / "system" / "brain.config.yaml"
    write_default_app_config(
        config_path,
        vault_path,
        agent="claude-code",
        folder_overrides={"daily_folder": "Daily", "thoughts_folder": "Thoughts"},
    )

    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert data["vault"]["daily_folder"] == "Daily"
    assert data["vault"]["thoughts_folder"] == "Thoughts"
