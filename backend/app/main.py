"""FastAPI application entrypoint.

Besides the usual REST routers, this app is the MCP **host** for the Gmail MCP
server: see ``app/mcp/host.py`` for the lifespan (session manager) and the
``/mcp-server`` mount.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, emails, drafts
from app.routers import settings as settings_router
from app.mcp.host import mcp_lifespan, mount_mcp_server
from app.mcp.server import GMAIL_TOOLS
from app.core.auth import GoogleReauthRequired

config = get_settings()


app = FastAPI(title="Gmail Reply Agent", version="0.1.0", lifespan=mcp_lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[config.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(GoogleReauthRequired)
async def _reauth_required(_req: Request, exc: GoogleReauthRequired):
    # A dead Google refresh token is a session problem, not a server fault:
    # 401 makes the SPA clear its JWT and send the user back to /login.
    return JSONResponse(
        status_code=401,
        content={"detail": "Google session expired — please sign in again."},
    )


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(emails.router, prefix="/emails", tags=["emails"])
app.include_router(drafts.router, prefix="/drafts", tags=["drafts"])
app.include_router(settings_router.router, prefix="/settings", tags=["settings"])

mount_mcp_server(app)  # /mcp-server, for external MCP clients / remote mode


@app.get("/health")
async def health():
    return {"status": "ok", "mcp_tools": GMAIL_TOOLS}


if __name__ == "__main__":
    from urllib.parse import urlparse

    import uvicorn

    # Derive the port from BACKEND_URL instead of hardcoding it. A literal 8000
    # here while .env says 8001 is the classic "login loops" bug: Google
    # redirects to the URI it was registered with, and nothing is listening.
    port = urlparse(config.backend_url).port or 8000
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
