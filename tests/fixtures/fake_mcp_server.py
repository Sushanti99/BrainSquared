"""A tiny stand-in for an app's MCP server, used by the gateway tests."""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("fake-app")


@mcp.tool()
def list_messages(limit: int = 2) -> str:
    """List recent messages."""
    return ", ".join(f"message {i}" for i in range(1, limit + 1))


@mcp.tool()
def send_message(to: str, text: str) -> str:
    """Send a message."""
    return f"sent to {to}: {text}"


@mcp.tool()
def get_expired() -> str:
    """Read something whose login has expired."""
    raise RuntimeError("invalid_grant: login expired")


if __name__ == "__main__":
    mcp.run()
