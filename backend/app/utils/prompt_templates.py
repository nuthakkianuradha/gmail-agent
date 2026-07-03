"""Backward-compatible prompt exports.

The reply prompts now live in the agent blocks (their canonical home):
- system prompt  -> :mod:`app.agent.system_prompt`
- user template  -> :mod:`app.agent.input`

They are re-exported here under their original names so existing imports (and
tests) keep working. The diff-summary prompt — used by the modification/learning
path, not the reply agent — stays defined here.
"""

from app.agent.system_prompt import REPLY_SYSTEM_PROMPT as DRAFT_SYSTEM_PROMPT
from app.agent.input import REPLY_INPUT_TEMPLATE as DRAFT_PROMPT

DIFF_SUMMARY_PROMPT = """Compare the AI-generated draft with the user's edited version.
Summarize what the user changed in 1-2 sentences. Focus on style, tone, and content preferences.

AI DRAFT:
{draft_before}

USER'S VERSION:
{draft_after}

Summary of changes:"""

__all__ = ["DRAFT_SYSTEM_PROMPT", "DRAFT_PROMPT", "DIFF_SUMMARY_PROMPT"]


if __name__ == "__main__":
    prompt = DRAFT_PROMPT.format(
        display_name="John",
        tone="professional",
        style_notes="Keep it concise",
        signature="Best, John",
        custom_instructions="No exclamation marks",
        rules_text="- Always be formal\n- CC assistant on project emails",
        past_emails_text="(no similar past emails found)",
        modifications_text="(no past modifications)",
        from_address="client@example.com",
        subject="Project Update",
        body_text="Hi John, can you send me the latest report?",
    )
    print("Sample prompt:")
    print(prompt[:500])
    print("...")
    print("Prompt templates OK (re-exported from app.agent blocks)")
