"""Interactive Claude-powered chat CLI across all your data."""
import anthropic
import config
from context_builder import build_context, ContextBundle

SYSTEM_PROMPT = """\
You are a personal assistant with full access to the user's Obsidian vault, Gmail, Google Calendar, and Notion.

Your job is to help them stay organized, prioritize their day, and think through what matters. \
You have their actual data — tasks, emails, calendar events, and notes — so be specific and concrete. \
Reference real items from their data when relevant. Don't give generic advice.

Current data:

{context}"""

COMMANDS = {
    "/daily": "Generate today's daily note in Obsidian",
    "/refresh": "Reload all data sources and reset conversation",
    "/quit":   "Exit",
    "/help":   "Show this list",
}


def run():
    if not config.ANTHROPIC_API_KEY:
        print("[error] ANTHROPIC_API_KEY not set in .env")
        return

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    bundle = build_context()
    messages: list[dict] = []

    print("\nReady. Type a message or /help for commands.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            print("Bye.")
            break

        if user_input == "/help":
            for cmd, desc in COMMANDS.items():
                print(f"  {cmd:<10} {desc}")
            print()
            continue

        if user_input == "/refresh":
            bundle = build_context()
            messages = []
            print("[refreshed — conversation reset]\n")
            continue

        if user_input == "/daily":
            from daily_note import generate
            path = generate(bundle)
            print(f"[daily note written to {path}]\n")
            continue

        messages.append({"role": "user", "content": user_input})
        system = SYSTEM_PROMPT.format(context=bundle.to_prompt_text())

        print("Claude: ", end="", flush=True)
        response_text = ""

        with client.messages.stream(
            model=config.ANTHROPIC_MODEL,
            max_tokens=1024,
            system=system,
            messages=messages,
        ) as stream:
            for chunk in stream.text_stream:
                print(chunk, end="", flush=True)
                response_text += chunk

        print("\n")
        messages.append({"role": "assistant", "content": response_text})
