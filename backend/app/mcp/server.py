"""MCP **server** — exposes Gmail as MCP tools.

A :class:`FastMCP` instance hosts the Gmail toolset. Each tool reads the caller's
Gmail OAuth access token from the ``X-Gmail-Access-Token`` request header
(injected by the client, see ``connection.py``) and delegates the actual Google
API work to :mod:`app.services.gmail_service`.

The server speaks the real MCP protocol over streamable HTTP. The resulting ASGI
app (``mcp_asgi_app``) is mounted into the FastAPI app *and* used in-process by
the agent's MCP client via an ASGI transport — same protocol either way.

The server is built by :func:`build_gmail_mcp` so tests can spin up an isolated
instance (a streamable-HTTP session manager can only be run once per instance).
The module-level ``mcp`` / ``mcp_asgi_app`` are the singletons used in production.
"""

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from app.services import gmail_service

# Names of the tools this server exposes (kept in sync with the definitions in
# ``build_gmail_mcp``). Handy for docs, health checks, and tests.
GMAIL_TOOLS = [
    "gmail_list_inbox",
    "gmail_get_message",
    "gmail_get_thread",
    "gmail_send_reply",
]


def _require_access_token(ctx: Context) -> str:
    """Pull the per-user Gmail access token out of the MCP request headers.

    The client attaches it as ``X-Gmail-Access-Token`` (see ``connection.py``).
    Raises if it is missing so a tool never runs without a caller identity.
    """
    request = ctx.request_context.request
    token = request.headers.get("x-gmail-access-token") if request else None
    if not token:
        raise ValueError("Missing X-Gmail-Access-Token header on MCP request")
    return token


def build_gmail_mcp() -> tuple[FastMCP, Starlette]:
    """Construct a fresh Gmail MCP server and its streamable-HTTP ASGI app.

    ``stateless_http`` keeps every request self-contained (no server-side session
    to persist) — ideal for short-lived, per-request agent calls. DNS-rebinding
    protection is disabled because the client reaches the app in-process via an
    ASGI transport (there is no real socket / Host to guard).
    """
    mcp = FastMCP(
        "gmail-agent-tools",
        instructions="Gmail tools for the reply agent: list inbox, read messages/threads, send replies.",
        stateless_http=True,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )

    @mcp.tool(description="List the user's Primary inbox messages (metadata only).")
    def gmail_list_inbox(
        ctx: Context,
        page_token: str | None = None,
        max_results: int = 20,
    ) -> dict:
        token = _require_access_token(ctx)
        return gmail_service.list_inbox(token, page_token, max_results)

    @mcp.tool(description="Fetch a single full email message by its Gmail message id.")
    def gmail_get_message(ctx: Context, message_id: str) -> dict:
        token = _require_access_token(ctx)
        return gmail_service.get_message(token, message_id)

    @mcp.tool(description="Fetch every message in a Gmail thread by thread id.")
    def gmail_get_thread(ctx: Context, thread_id: str) -> dict:
        token = _require_access_token(ctx)
        return gmail_service.get_thread(token, thread_id)

    @mcp.tool(description="Send a reply email within the correct Gmail thread.")
    def gmail_send_reply(
        ctx: Context,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        message_id_header: str,
    ) -> dict:
        token = _require_access_token(ctx)
        return gmail_service.send_reply(
            access_token=token,
            to=to,
            subject=subject,
            body=body,
            thread_id=thread_id,
            message_id_header=message_id_header,
        )

    return mcp, mcp.streamable_http_app()


# Production singletons: mounted into FastAPI (external MCP endpoint) and driven
# in-process by the agent's client. Reuse the SAME instance in both places so the
# running session manager (started in the app lifespan) is the one the in-process
# transport talks to.
mcp, mcp_asgi_app = build_gmail_mcp()


if __name__ == "__main__":
    print("MCP server: gmail-agent-tools")
    print(f"  Streamable-HTTP path: {mcp.settings.streamable_http_path}")
    print(f"  Tools exposed ({len(GMAIL_TOOLS)}):")
    for name in GMAIL_TOOLS:
        print(f"    - {name}")
    print("MCP server module OK")
