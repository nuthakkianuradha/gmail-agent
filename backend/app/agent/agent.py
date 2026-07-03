"""The reply agent orchestrator.

Wires the five blocks together for the two things the agent does:

    generate_reply(message_id)   config → [Gmail via MCP] → state → input → LLM → output
    send_reply(...)              [Gmail via MCP] → archive + learn from edits

The agent reaches Gmail **exclusively** through the MCP client — it never calls
the Gmail SDK or touches an OAuth token beyond handing it to the client.
"""

from app.agent.config import AgentConfig
from app.agent.state import AgentState
from app.agent.input import build_input
from app.agent.system_prompt import build_system_prompt
from app.agent.output import ReplyAgentOutput, parse_output
from app.mcp.client import GmailMCPClient
from app.services import auth_service, archive_service
from app.services.llm_service import generate_draft
from app.services.modification_service import store_modification


class ReplyAgent:
    """Per-user reply agent. Construct from the authenticated user record."""

    def __init__(self, user: dict, config: AgentConfig | None = None):
        self.user = user
        self.config = config or AgentConfig.default()
        # Decrypt once; the token is only ever handed to the MCP client.
        self._access_token = auth_service.get_decrypted_access_token(user)

    def _gmail(self) -> GmailMCPClient:
        return GmailMCPClient(self._access_token)

    async def generate_reply(self, gmail_message_id: str) -> ReplyAgentOutput:
        """Run the full generate pipeline and return a structured draft."""
        # 1. INPUT SOURCE — fetch the email to reply to over MCP.
        async with self._gmail() as gmail:
            email = await gmail.get_message(gmail_message_id)

        # 2. STATE — load persona, rules, and RAG memory for this email.
        state = AgentState.load(self.user["id"], email, self.config)

        # 3. SYSTEM PROMPT + INPUT — assemble the model turns.
        system_prompt = build_system_prompt()
        user_prompt = build_input(email, state)

        # 4. MODEL — generate, governed by CONFIG.
        raw = await generate_draft(
            system_prompt,
            user_prompt,
            primary_model=self.config.primary_model,
            fallback_model=self.config.fallback_model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # 5. OUTPUT — parse into a clean, structured result.
        return parse_output(raw, context_used=state.context_count)

    async def send_reply(
        self,
        gmail_thread_id: str,
        gmail_message_id: str,
        to: str,
        subject: str,
        body: str,
        draft_before: str | None = None,
    ) -> dict:
        """Send the reply over MCP, archive it, and learn from any user edits."""
        async with self._gmail() as gmail:
            # Need the original message's Message-ID header for correct threading.
            original = await gmail.get_message(gmail_message_id)
            sent = await gmail.send_reply(
                to=to,
                subject=subject,
                body=body,
                thread_id=gmail_thread_id,
                message_id_header=original.get("message_id_header", ""),
            )

        gmail_sent_id = sent.get("id", "")

        # Archive the sent email into long-term memory (also embeds it for RAG).
        archive_service.archive_sent_email(
            user_id=self.user["id"],
            gmail_message_id=gmail_sent_id,
            gmail_thread_id=gmail_thread_id,
            from_address=self.user["email"],
            to_address=to,
            subject=subject,
            body_text=body,
        )

        # STATE UPDATE / LEARNING — if the user edited the AI draft, record the
        # before/after so future retrievals reflect their preferences.
        if draft_before and draft_before != body:
            await store_modification(
                user_id=self.user["id"],
                email_id=None,
                subject=subject,
                snippet=original.get("snippet", ""),
                draft_before=draft_before,
                draft_after=body,
            )

        return {"status": "sent", "gmail_message_id": gmail_sent_id}


if __name__ == "__main__":
    print("ReplyAgent — orchestrates the 5 agent blocks over the MCP client")
    print("  generate_reply(gmail_message_id) -> ReplyAgentOutput")
    print("  send_reply(thread_id, message_id, to, subject, body, draft_before?) -> dict")
    print("  blocks: config, system_prompt, state, input, output")
    print("ReplyAgent module OK")
