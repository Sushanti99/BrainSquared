"""Entry point.

Usage:
  python main.py daily          # generate today's Obsidian daily note
  python main.py chat           # interactive chat with your data via Claude
  python main.py daily --vault /path/to/vault   # override vault path
"""
import argparse
from pathlib import Path


def cmd_daily(args):
    from context_builder import build_context
    from daily_note import generate
    import config

    vault = Path(args.vault) if args.vault else config.VAULT_PATH
    bundle = build_context()
    path = generate(bundle, vault_path=vault)
    print(f"\nDaily note written: {path}")


def cmd_chat(_args):
    from chat import run
    run()


def main():
    parser = argparse.ArgumentParser(
        description="todos-with-obsidian — Obsidian daily notes + AI chat across your data"
    )
    parser.add_argument("--vault", help="Override vault path from .env", default=None)
    sub = parser.add_subparsers(dest="command")
    sub.required = True

    p_daily = sub.add_parser("daily", help="Generate today's daily note in Obsidian")
    p_daily.set_defaults(func=cmd_daily)

    p_chat = sub.add_parser("chat", help="Chat with your data via Claude")
    p_chat.set_defaults(func=cmd_chat)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
