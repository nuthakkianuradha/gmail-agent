"""Agent block: **state**.

Everything the agent knows about the user and the situation, loaded from
persistent memory: the user's persona, their active rules, and the RAG-retrieved
neighbours (similar past emails and past edits). This is the dynamic context the
``input`` block renders into a prompt.

The heavy lifting (vector search, DB reads) stays in :mod:`app.services.rag_service`;
this block just gathers the pieces into one immutable snapshot.
"""

from dataclasses import dataclass, field

from app.agent.config import AgentConfig
from app.services import rag_service


@dataclass(frozen=True)
class AgentState:
    persona: dict
    rules: list[dict] = field(default_factory=list)
    past_emails: list[dict] = field(default_factory=list)
    modifications: list[dict] = field(default_factory=list)

    @property
    def context_count(self) -> int:
        """Number of retrieved memory items that informed this reply."""
        return len(self.past_emails) + len(self.modifications)

    @classmethod
    def load(
        cls,
        user_id: str,
        email_data: dict,
        config: AgentConfig | None = None,
    ) -> "AgentState":
        """Assemble the agent's state from memory for one incoming email."""
        config = config or AgentConfig.default()

        email_text = (
            f"Subject: {email_data.get('subject', '')}\n"
            f"{email_data.get('body_text', '')}"
        )
        context = rag_service.retrieve_context(
            user_id,
            email_text,
            match_count=config.match_count,
            match_threshold=config.match_threshold,
            source_types=config.memory_source_types,
        )

        past_emails = [c for c in context if c.get("source_type") == "email"]
        modifications = [c for c in context if c.get("source_type") == "modification"]

        return cls(
            persona=rag_service.get_persona(user_id),
            rules=rag_service.get_active_rules(user_id),
            past_emails=past_emails,
            modifications=modifications,
        )


if __name__ == "__main__":
    # Construct a state snapshot directly (no DB) to show its shape.
    state = AgentState(
        persona={"display_name": "John", "tone": "professional"},
        rules=[{"rule_text": "Always be concise"}],
        past_emails=[{"content_text": "Subject: Hi\nBody", "similarity": 0.82}],
        modifications=[],
    )
    print("AgentState snapshot:")
    print(f"  persona:      {state.persona}")
    print(f"  rules:        {len(state.rules)}")
    print(f"  past_emails:  {len(state.past_emails)}")
    print(f"  modifications:{len(state.modifications)}")
    print(f"  context_count:{state.context_count}")
    print("State module OK")
