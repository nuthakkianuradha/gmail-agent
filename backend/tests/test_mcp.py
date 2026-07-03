"""Tests for the MCP layer: a real in-process protocol roundtrip.

These exercise the actual MCP wire protocol (initialize -> list_tools ->
call_tool) via the ASGI transport, with the Gmail SDK stubbed so no Google call
is made. They prove the client, connection, and server modules fit together and
that the per-user token is propagated over the request header.

Each test gets its own isolated MCP server instance because a streamable-HTTP
session manager can only be run once per instance.
"""

import anyio
import pytest

from app.mcp import server, connection
from app.mcp.server import build_gmail_mcp, GMAIL_TOOLS
from app.mcp.client import GmailMCPClient
from app.services import gmail_service


@pytest.fixture
def mcp_app(monkeypatch):
    """A fresh Gmail MCP server app, wired up as the in-process transport target."""
    fresh_mcp, fresh_app = build_gmail_mcp()
    # Point the client's in-process transport at this test's server instance.
    monkeypatch.setattr(connection, "mcp_asgi_app", fresh_app)
    return fresh_app


def run_with_mcp(mcp_app, coro_factory):
    """Run an async scenario with the server's session manager active."""

    async def scenario():
        async with mcp_app.router.lifespan_context(mcp_app):
            return await coro_factory()

    return anyio.run(scenario)


def test_mcp_lists_gmail_tools(mcp_app):
    async def scenario():
        async with GmailMCPClient("tok") as gmail:
            return await gmail.list_tools()

    tools = run_with_mcp(mcp_app, scenario)
    assert set(GMAIL_TOOLS).issubset(set(tools))


def test_mcp_get_message_flows_token_and_parses_result(mcp_app, monkeypatch):
    captured = {}

    def fake_get_message(token, message_id):
        captured["token"] = token
        captured["message_id"] = message_id
        return {"gmail_message_id": message_id, "subject": "Hello", "message_id_header": "<x@y>"}

    monkeypatch.setattr(gmail_service, "get_message", fake_get_message)

    async def scenario():
        async with GmailMCPClient("USER_TOKEN_123") as gmail:
            return await gmail.get_message("m1")

    msg = run_with_mcp(mcp_app, scenario)

    # Result parsed back into a plain dict...
    assert msg["subject"] == "Hello"
    assert msg["gmail_message_id"] == "m1"
    # ...and the per-user token reached the server-side tool over the MCP header.
    assert captured["token"] == "USER_TOKEN_123"
    assert captured["message_id"] == "m1"


def test_mcp_send_reply_passes_all_arguments(mcp_app, monkeypatch):
    captured = {}

    def fake_send_reply(**kwargs):
        captured.update(kwargs)
        return {"id": "sent-1"}

    monkeypatch.setattr(gmail_service, "send_reply", fake_send_reply)

    async def scenario():
        async with GmailMCPClient("TOK") as gmail:
            return await gmail.send_reply(
                to="a@b.com",
                subject="Re: Hi",
                body="Thanks!",
                thread_id="t1",
                message_id_header="<orig@x>",
            )

    sent = run_with_mcp(mcp_app, scenario)
    assert sent["id"] == "sent-1"
    assert captured["access_token"] == "TOK"
    assert captured["to"] == "a@b.com"
    assert captured["thread_id"] == "t1"
    assert captured["message_id_header"] == "<orig@x>"


def test_mcp_missing_token_is_rejected(mcp_app):
    """A tool call with no access token must error (never runs unauthenticated)."""

    async def scenario():
        # Bypass the client's header injection by opening a raw session with no token.
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
        from app.mcp.connection import _inprocess_client_factory, _mcp_endpoint, _INPROCESS_BASE_URL

        endpoint = _mcp_endpoint(_INPROCESS_BASE_URL)
        async with streamablehttp_client(
            endpoint, headers={}, httpx_client_factory=_inprocess_client_factory
        ) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                return await session.call_tool("gmail_get_message", {"message_id": "m1"})

    result = run_with_mcp(mcp_app, scenario)
    assert result.isError


if __name__ == "__main__":
    print("Run with: pytest tests/test_mcp.py")
