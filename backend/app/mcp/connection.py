"""MCP **connection** — transport + session wiring between client and server.

This module is the single place that knows *how* an MCP client reaches the
server and how the per-user Gmail token rides along with the request.

Two transports are supported, both speaking the real MCP protocol:

- **in-process** (default): an ``httpx`` ASGI transport pointed straight at the
  mounted :data:`app.mcp.server.mcp_asgi_app`. No sockets, so it works in a
  single Railway service and in tests, while still exercising the full
  JSON-RPC-over-streamable-HTTP protocol.
- **remote**: a normal networked streamable-HTTP connection to
  ``settings.mcp_server_url`` when the MCP server is deployed separately.

The per-user OAuth token is passed as the :data:`TOKEN_HEADER` header on every
request; the server reads it back out (see ``server._require_access_token``).
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from app.config import get_settings
from app.mcp.server import mcp, mcp_asgi_app

# Header used to carry the caller's Gmail OAuth access token to the server.
TOKEN_HEADER = "X-Gmail-Access-Token"

# Base URL only matters for building request lines; with the ASGI transport no
# DNS/socket resolution happens, so this is an internal placeholder.
_INPROCESS_BASE_URL = "http://gmail-agent-mcp.internal"


def _mcp_endpoint(base_url: str) -> str:
    """Join a base URL with the server's streamable-HTTP path (e.g. ``/mcp``)."""
    path = mcp.settings.streamable_http_path
    return f"{base_url.rstrip('/')}{path}"


def _inprocess_client_factory(headers=None, timeout=None, auth=None) -> httpx.AsyncClient:
    """httpx client factory that routes MCP requests through the ASGI app.

    Signature matches ``mcp.shared._httpx_utils.McpHttpClientFactory`` so it can
    be handed to :func:`streamablehttp_client`.
    """
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=mcp_asgi_app),
        base_url=_INPROCESS_BASE_URL,
        headers=headers,
        timeout=timeout if timeout is not None else 30,
        auth=auth,
    )


@asynccontextmanager
async def open_session(access_token: str) -> AsyncIterator[ClientSession]:
    """Open an initialized MCP :class:`ClientSession` for one caller.

    The ``access_token`` is attached as :data:`TOKEN_HEADER` so server-side tools
    can act on behalf of that user. Yields a session that is ready for
    ``list_tools`` / ``call_tool`` and is torn down on exit.
    """
    settings = get_settings()
    headers = {TOKEN_HEADER: access_token}

    if settings.mcp_server_url:
        # Remote server, real network transport.
        endpoint = _mcp_endpoint(settings.mcp_server_url)
        transport_cm = streamablehttp_client(endpoint, headers=headers)
    else:
        # Default: in-process ASGI transport against the mounted server app.
        endpoint = _mcp_endpoint(_INPROCESS_BASE_URL)
        transport_cm = streamablehttp_client(
            endpoint,
            headers=headers,
            httpx_client_factory=_inprocess_client_factory,
        )

    async with transport_cm as (read_stream, write_stream, _get_session_id):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


if __name__ == "__main__":
    import anyio

    async def _smoke() -> None:
        settings = get_settings()
        mode = "remote" if settings.mcp_server_url else "in-process (ASGI)"
        print(f"MCP connection transport: {mode}")
        print(f"  Token header: {TOKEN_HEADER}")
        print(f"  Endpoint: {_mcp_endpoint(settings.mcp_server_url or _INPROCESS_BASE_URL)}")
        # Prove the transport actually connects and lists tools (needs the
        # server's session manager, so run within its lifespan).
        async with mcp_asgi_app.router.lifespan_context(mcp_asgi_app):
            async with open_session("smoke-test-token") as session:
                tools = await session.list_tools()
                print(f"  Tools visible over MCP: {[t.name for t in tools.tools]}")
        print("MCP connection module OK")

    anyio.run(_smoke)
