"""MCP (Model Context Protocol) layer — Gmail exposed as **tools** over the real protocol.

MCP has a handful of named roles. One file per role, read in this order:

    gmail.py       1 CAPABILITY  the thing being exposed: a plain Gmail SDK wrapper (no MCP in it)
    email_parser.py               helper for gmail.py (MIME/payload parsing)
    server.py      2 SERVER      owns the capability as 4 tools (gmail_list_inbox, _get_message, _get_thread, _send_reply)
    transport.py   3 TRANSPORT   how JSON-RPC messages move: in-process ASGI (default) or remote streamable HTTP;
                                 carries the per-user token in the X-Gmail-Access-Token header
    client.py      4 CLIENT      GmailMCPClient: one session, typed methods, dicts in/out
    host.py        5 HOST        the FastAPI app: starts the server's session manager, mounts it at /mcp-server

Flow of one call:

    agent/router ──GmailMCPClient(token)──▶ transport ──JSON-RPC──▶ server ──▶ gmail.py ──▶ Gmail API

Depends on nothing else in the app except ``app.config`` (for ``MCP_SERVER_URL``).
"""

from app.mcp.client import GmailMCPClient
from app.mcp.server import GMAIL_TOOLS, mcp, mcp_asgi_app
from app.mcp.transport import TOKEN_HEADER, open_session

__all__ = [
    "mcp",
    "mcp_asgi_app",
    "GMAIL_TOOLS",
    "GmailMCPClient",
    "TOKEN_HEADER",
    "open_session",
]
