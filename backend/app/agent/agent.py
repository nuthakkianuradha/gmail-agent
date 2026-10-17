"""The reply agent orchestrator.

Wires the six blocks together for the two things the agent does:

    generate_reply(message_id)   config → tools.get_email → state → system_prompt + input → model → output
    send_reply(...)              tools.get_email → tools.send_reply → tools.remember_sent_email (+ remember_edit)

Side effects (Gmail, memory writes) go through the **tools** block only. The
orchestrator holds no Gmail client and no DB handle of its own.
"""

from app.agent.config import AgentConfig
from app.agent.input import build_input
from app.agent.output import ReplyAgentOutput, parse_output
from app.agent.state import AgentState
from app.agent.system_prompt import build_system_prompt
from app.agent.tools import AgentTools
from app.core import auth, llm


class ReplyAgent:
    """Per-user reply agent. Construct from the authenticated user record."""

    def __init__(self, user: dict, config: AgentConfig | None = None):
        self.user = user
        self.config = config or AgentConfig.default()
        # Decrypt once; the token lives only inside the tools block.
        self.tools = AgentTools(
            user_id=user["id"],
            user_email=user["email"],
            access_token=auth.get_decrypted_access_token(user),
        )

    async def generate_reply(self, gmail_message_id: str) -> ReplyAgentOutput:
        """Run the full generate pipeline and return a structured draft."""
        # TOOLS — fetch the email to reply to (over MCP).
        email = await self.tools.get_email(gmail_message_id)

        # STATE — persona, rules, and RAG memory for this email.
        state = AgentState.load(self.user["id"], email, self.config)

        # SYSTEM PROMPT + INPUT — assemble the model turns.
        system_prompt = build_system_prompt()
        user_prompt = build_input(email, state)

        # MODEL — governed by CONFIG.
        raw = await llm.chat(
            user_prompt,
            system_prompt=system_prompt,
            model=self.config.primary_model,
            fallback_model=self.config.fallback_model,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        # OUTPUT — parse into a clean, structured result.
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
        """Send the reply, remember it, and learn from any user edits."""
        # TOOLS — the original message's Message-ID header is needed for threading.
        original = await self.tools.get_email(gmail_message_id)
        sent = await self.tools.send_reply(
            to=to,
            subject=subject,
            body=body,
            thread_id=gmail_thread_id,
            message_id_header=original.get("message_id_header", ""),
        )
        gmail_sent_id = sent.get("id", "")

        # TOOLS — grow memory: the sent email, and the edit if there was one.
        self.tools.remember_sent_email(
            gmail_message_id=gmail_sent_id,
            gmail_thread_id=gmail_thread_id,
            to=to,
            subject=subject,
            body=body,
        )
        if draft_before and draft_before != body:
            await self.tools.remember_edit(
                subject=subject,
                snippet=original.get("snippet", ""),
                draft_before=draft_before,
                draft_after=body,
            )

        return {"status": "sent", "gmail_message_id": gmail_sent_id}


if __name__ == "__main__":
    print("ReplyAgent — orchestrates the 6 agent blocks")
    print("  generate_reply(gmail_message_id) -> ReplyAgentOutput")
    print("  send_reply(thread_id, message_id, to, subject, body, draft_before?) -> dict")
    print("  blocks: config, system_prompt, state, input, output, tools")
    print("ReplyAgent module OK")
