"""`uv run python -m app.agent` — smoke-check the agent's five blocks without
any network: build a state snapshot, render the prompts, parse an output."""

from app.agent.config import AgentConfig
from app.agent.input import build_input
from app.agent.output import parse_output
from app.agent.state import AgentState
from app.agent.system_prompt import build_system_prompt

print("Agent subsystem (5 blocks + orchestrator)")
cfg = AgentConfig.default()
print(f"  1 config:        primary_model={cfg.primary_model!r}, retrieval k={cfg.match_count} thr={cfg.match_threshold}")
sp = build_system_prompt()
print(f"  2 system_prompt: {len(sp)} chars")
state = AgentState(
    persona={"display_name": "Ada", "tone": "friendly", "style_notes": "", "signature": "— Ada", "custom_instructions": ""},
    rules=[{"rule_text": "Keep replies under 80 words"}],
    past_emails=[{"content_text": "Subject: Lunch\nSure, noon works.", "similarity": 0.81}],
    modifications=[],
)
print(f"  3 state:         persona+{len(state.rules)} rule(s), context_count={state.context_count}")
email = {"from_address": "sam@example.com", "subject": "Lunch Thursday?", "body_text": "Free at noon?"}
up = build_input(email, state)
print(f"  4 input:         {len(up)} chars rendered from state + email")
out = parse_output("```\nSure, noon works for me.\n```", context_used=state.context_count)
print(f"  5 output:        {out.draft!r} (context_used={out.context_used})")
print("  orchestrator:    ReplyAgent.generate_reply / send_reply  (uses app.mcp + app.rag + app.core.llm)")
print("Agent subsystem OK")
