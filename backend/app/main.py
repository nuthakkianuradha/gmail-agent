"""FastAPI application entrypoint.

Besides the usual REST routers, this app hosts the Gmail **MCP server**:

- Its session manager is started in the app ``lifespan`` (required — the
  in-process MCP client the agent uses talks to this running manager).
- The MCP ASGI app is also mounted at ``/mcp-server`` so external MCP clients
  (or a separately deployed backend pointed at us via ``MCP_SERVER_URL``) can
  reach the same tools over the network.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, emails, drafts
from app.routers import settings as settings_router
from app.mcp.server import mcp_asgi_app, GMAIL_TOOLS

config = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Start the MCP streamable-HTTP session manager for the whole app lifetime.
    # Without this, in-process tool calls fail with "Task group is not initialized".
    async with mcp_asgi_app.router.lifespan_context(mcp_asgi_app):
        yield


app = FastAPI(title="Gmail Reply Agent", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(emails.router, prefix="/emails", tags=["emails"])
app.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])

# Expose the MCP server over the network (in-process transport is the default;
# this mount is for external MCP clients / remote-mode deployments).
app.mount("/mcp-server", mcp_asgi_app)


@app.get("/health")
async def health():
    return {"status": "ok", "mcp_tools": GMAIL_TOOLS}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
