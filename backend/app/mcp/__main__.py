"""`uv run python -m app.mcp` — smoke-check the MCP subsystem: spin up the
in-process server, open a real MCP session, and list the Gmail tools."""

import asyncio

from app.mcp.connection import open_session
from app.mcp.server import GMAIL_TOOLS, mcp_asgi_app


async def main() -> None:
    print("MCP subsystem")
    async with mcp_asgi_app.router.lifespan_context(mcp_asgi_app):
        async with open_session("smoke-test-token") as session:
            tools = await session.list_tools()
            names = sorted(t.name for t in tools.tools)
    print(f"  server:     FastMCP exposes {len(names)} tools: {', '.join(names)}")
    print(f"  connection: in-process ASGI transport, token sent as X-Gmail-Access-Token")
    print(f"  client:     GmailMCPClient wraps these tools; expected set = {sorted(GMAIL_TOOLS)}")
    assert names == sorted(GMAIL_TOOLS), "tool list drifted from GMAIL_TOOLS"
    print("MCP subsystem OK")


asyncio.run(main())
