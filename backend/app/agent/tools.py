"""Agent block: **tools**.

Everything the agent can *do* besides calling the model. Each tool is a small
method with a plain-dict in/out contract, backed by one of the other two
subsystems:

- Gmail tools  → ``app.mcp``  (``GmailMCPClient`` over the MCP protocol)
- Memory tools → ``app.rag``  (``learning``: archive sent mail, record edits)

The orchestrator never touches MCP or RAG directly for side effects; it calls
a tool. ``TOOLS`` is the human-readable registry of what the agent can do.
"""

from dataclasses import dataclass

from app.mcp.client import GmailMCPClient
from app.rag.learning import archive_sent_email, store_modification


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    backed_by: str


TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec("get_email", "Fetch one Gmail message (parsed) by id", "mcp: gmail_get_message"),
    ToolSpec("send_reply", "Send an in-thread reply via Gmail", "mcp: gmail_send_reply"),
    ToolSpec("remember_sent_email", "Archive + index a sent email for future recall", "rag.learning.archive_sent_email"),
    ToolSpec("remember_edit", "Record, summarize and index the user's edit of a draft", "rag.learning.store_modification"),
)


class AgentTools:
    """Per-user tool belt. Holds the Gmail token only to hand it to the MCP client."""

    def __init__(self, user_id: str, user_email: str, access_token: str):
        self.user_id = user_id
        self.user_email = user_email
        self._access_token = access_token

    # ---- Gmail (over MCP) -------------------------------------------------

    def _gmail(self) -> GmailMCPClient:
        return GmailMCPClient(self._access_token)

    async def get_email(self, gmail_message_id: str) -> dict:
        async with self._gmail() as gmail:
            return await gmail.get_message(gmail_message_id)

    async def send_reply(
        self,
        *,
        to: str,
        subject: str,
        body: str,
        thread_id: str,
        message_id_header: str,
    ) -> dict:
        async with self._gmail() as gmail:
            return await gmail.send_reply(
                to=to,
                subject=subject,
                body=body,
                thread_id=thread_id,
                message_id_header=message_id_header,
            )

    # ---- Memory (RAG learning loop) ---------------------------------------

    def remember_sent_email(
        self,
        *,
        gmail_message_id: str,
        gmail_thread_id: str,
        to: str,
        subject: str,
        body: str,
    ) -> dict:
        return archive_sent_email(
            user_id=self.user_id,
            gmail_message_id=gmail_message_id,
            gmail_thread_id=gmail_thread_id,
            from_address=self.user_email,
            to_address=to,
            subject=subject,
            body_text=body,
        )

    async def remember_edit(
        self,
        *,
        subject: str,
        snippet: str,
        draft_before: str,
        draft_after: str,
    ) -> dict:
        return await store_modification(
            user_id=self.user_id,
            email_id=None,
            subject=subject,
            snippet=snippet,
            draft_before=draft_before,
            draft_after=draft_after,
        )


if __name__ == "__main__":
    print("Agent tools:")
    for t in TOOLS:
        print(f"  {t.name:<20} {t.description:<58} [{t.backed_by}]")
    print("Tools module OK")
