"""`uv run python -m app.mcp` — walk the five MCP roles: start the server
(as the host would), open a transport + client session, list the tools."""

import asyncio

from app.mcp.host import MCP_MOUNT_PATH, mcp_lifespan
from app.mcp.server import GMAIL_TOOLS
from app.mcp.transport import TOKEN_HEADER, open_session


async def main() -> None:
    print("MCP subsystem — role walk-through")
    print("  1 capability: gmail.py wraps the Gmail SDK (plain functions, token passed in)")
    async with mcp_lifespan(None):  # 5 host: session manager running
        async with open_session("smoke-test-token") as session:  # 3 transport + 4 client
            names = sorted(t.name for t in (await session.list_tools()).tools)
    print(f"  2 server:     FastMCP exposes {len(names)} tools: {', '.join(names)}")
    print(f"  3 transport:  in-process ASGI, token in {TOKEN_HEADER}")
    print(f"  4 client:     GmailMCPClient wraps list_tools/call_tool into typed methods")
    print(f"  5 host:       mcp_lifespan() started the session manager; mounted at {MCP_MOUNT_PATH} for external clients")
    assert names == sorted(GMAIL_TOOLS), "tool list drifted from GMAIL_TOOLS"
    print("MCP subsystem OK")


asyncio.run(main())
