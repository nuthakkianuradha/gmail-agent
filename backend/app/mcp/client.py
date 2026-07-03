"""MCP **client** — the typed handle the agent uses to call Gmail tools.

:class:`GmailMCPClient` wraps an MCP :class:`ClientSession` (opened via
``connection.open_session``) and turns raw ``call_tool`` responses back into
plain dicts. The agent code depends only on this small surface — it never sees
JSON-RPC, transports, or the Gmail SDK.

Usage::

    async with GmailMCPClient(access_token) as gmail:
        email = await gmail.get_message(message_id)
        await gmail.send_reply(to=..., subject=..., body=..., ...)

A single ``async with`` block reuses one MCP session for all calls in a request.
"""

import json
from typing import Any

from mcp.types import CallToolResult

from app.mcp.connection import open_session


def _parse_tool_result(result: CallToolResult) -> Any:
    """Convert an MCP tool result into a plain Python value.

    Gmail tools return JSON objects. The MCP protocol carries that as a text
    content block (JSON-serialized) and, for object returns, as
    ``structuredContent``. We prefer the text block since it is unambiguous, and
    fall back to structured content.
    """
    if result.isError:
        text = result.content[0].text if result.content else "unknown error"
        raise RuntimeError(f"MCP tool error: {text}")

    for block in result.content:
        text = getattr(block, "text", None)
        if text is not None:
            return json.loads(text)

    if result.structuredContent is not None:
        sc = result.structuredContent
        # FastMCP wraps non-object returns under a "result" key.
        if isinstance(sc, dict) and set(sc.keys()) == {"result"}:
            return sc["result"]
        return sc

    return None


class GmailMCPClient:
    """High-level, per-user client for the Gmail MCP tools."""

    def __init__(self, access_token: str):
        self._access_token = access_token
        self._session_cm = None
        self._session = None

    async def __aenter__(self) -> "GmailMCPClient":
        self._session_cm = open_session(self._access_token)
        self._session = await self._session_cm.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self._session_cm.__aexit__(exc_type, exc, tb)
        self._session = None
        self._session_cm = None

    async def _call(self, tool: str, arguments: dict) -> Any:
        if self._session is None:
            raise RuntimeError(
                "GmailMCPClient must be used inside 'async with' before calling tools"
            )
        result = await self._session.call_tool(tool, arguments)
        return _parse_tool_result(result)

    # --- Gmail tool wrappers -------------------------------------------------

    async def list_tools(self) -> list[str]:
        """Return the tool names the server advertises (protocol handshake)."""
        listed = await self._session.list_tools()
        return [t.name for t in listed.tools]

    async def list_inbox(self, page_token: str | None = None, max_results: int = 20) -> dict:
        return await self._call(
            "gmail_list_inbox",
            {"page_token": page_token, "max_results": max_results},
        )

    async def get_message(self, message_id: str) -> dict:
        return await self._call("gmail_get_message", {"message_id": message_id})

    async def get_thread(self, thread_id: str) -> dict:
        return await self._call("gmail_get_thread", {"thread_id": thread_id})

    async def send_reply(
        self,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        message_id_header: str,
    ) -> dict:
        return await self._call(
            "gmail_send_reply",
            {
                "to": to,
                "subject": subject,
                "body": body,
                "thread_id": thread_id,
                "message_id_header": message_id_header,
            },
        )


if __name__ == "__main__":
    print("GmailMCPClient — MCP client wrapper for Gmail tools")
    print("  Methods: list_tools, list_inbox, get_message, get_thread, send_reply")
    print("  Usage: async with GmailMCPClient(token) as gmail: await gmail.get_message(id)")
    print("GmailMCPClient module OK (see tests/test_mcp.py for a live roundtrip)")
