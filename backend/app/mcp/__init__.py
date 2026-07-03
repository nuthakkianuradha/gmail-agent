"""MCP (Model Context Protocol) layer for the Gmail Reply Agent.

The agent never touches the Gmail API directly. Instead, Gmail is exposed as a
set of MCP *tools* over the real MCP wire protocol (streamable HTTP / JSON-RPC),
split into three concerns:

- ``server``      — the MCP server that hosts the Gmail tools.
- ``connection``  — the transport/session wiring between client and server,
                    including per-user OAuth token propagation.
- ``client``      — a high-level, typed client the agent uses to call the tools.
"""

from app.mcp.server import mcp, mcp_asgi_app, GMAIL_TOOLS
from app.mcp.client import GmailMCPClient
from app.mcp.connection import TOKEN_HEADER, open_session

__all__ = [
    "mcp",
    "mcp_asgi_app",
    "GMAIL_TOOLS",
    "GmailMCPClient",
    "TOKEN_HEADER",
    "open_session",
]
