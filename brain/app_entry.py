"""Mac app entry point — headless server, no browser, signals ready via stdout."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="BrainSquared server")
    parser.add_argument("--vault", required=True, help="Path to Brain vault")
    parser.add_argument("--port", type=int, default=3000, help="Preferred server port")
    args = parser.parse_args()

    vault_path = Path(args.vault).expanduser().resolve()

    # Env file lives in app support dir — always create the dir and file so
    # load_env_config uses it as the base path (avoids writing token.json to /)
    app_support = Path.home() / "Library" / "Application Support" / "BrainSquared"
    app_support.mkdir(parents=True, exist_ok=True)
    env_file = app_support / ".env"
    if not env_file.exists():
        env_file.write_text("")

    from brain.app_config import load_app_config
    from brain.env_config import load_env_config
    from brain.server import run_server

    try:
        app_cfg = load_app_config(vault_path=vault_path, port_override=args.port)
    except FileNotFoundError as exc:
        print(f"ERROR:{exc}", flush=True)
        return 1

    env_cfg = load_env_config(env_file=env_file)
    # Signal Swift: server is about to bind — Swift polls HTTP instead of reading this
    # but we print for debugging
    print(f"STARTING:{app_cfg.server.port}", flush=True)
    run_server(app_cfg, env_cfg, open_browser=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
