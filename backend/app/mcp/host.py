"""MCP role 5 — **HOST**. The application that embeds the server and spawns clients.

In MCP the *host* is the program the user actually runs (an IDE, a chat app —
here, our FastAPI backend). It owns the lifecycle of the server and decides
when a client is created. Concretely this module gives ``main.py`` two things:

- :func:`mcp_lifespan` — starts the server's streamable-HTTP **session
  manager** for the life of the app. Without it, every in-process tool call
  fails with *"Task group is not initialized"*. This is the most important
  line of wiring in the whole MCP layer.
- :func:`mount_mcp_server` — mounts the server's ASGI app at ``/mcp-server``
  so *external* MCP clients (or a separately deployed backend in remote mode)
  can reach the same tools over the network. The in-process transport does
  not need this mount; it talks to the ASGI app object directly.

Clients are created per user, per request, by the agent's tools block and the
email router: ``GmailMCPClient(access_token)``.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.mcp.server import GMAIL_TOOLS, mcp_asgi_app

MCP_MOUNT_PATH = "/mcp-server"


@asynccontextmanager
async def mcp_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Run the MCP server's session manager for the whole app lifetime."""
    async with mcp_asgi_app.router.lifespan_context(mcp_asgi_app):
        yield


def mount_mcp_server(app: FastAPI, path: str = MCP_MOUNT_PATH) -> None:
    """Expose the MCP server over HTTP for external clients / remote mode."""
    app.mount(path, mcp_asgi_app)


if __name__ == "__main__":
    print("HOST: the FastAPI app embeds the MCP server")
    print("  mcp_lifespan(app)        starts the session manager (required for in-process calls)")
    print(f"  mount_mcp_server(app)    mounts the server at {MCP_MOUNT_PATH} for external MCP clients")
    print(f"  tools hosted: {GMAIL_TOOLS}")
    print("Host module OK")
