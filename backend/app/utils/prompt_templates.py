DRAFT_SYSTEM_PROMPT = """You are an email reply assistant. Draft a reply to the email below.
Follow the user's persona, rules, and learned preferences exactly.
Write ONLY the reply body — no subject line, no headers, no meta-commentary."""

DRAFT_PROMPT = """
USER PERSONA:
- Name: {display_name}
- Tone: {tone}
- Style: {style_notes}
- Signature: {signature}
- Instructions: {custom_instructions}

RULES:
{rules_text}

RELEVANT PAST EMAILS (for context and style reference):
{past_emails_text}

LEARNED PREFERENCES (from past edits):
{modifications_text}

EMAIL TO REPLY TO:
From: {from_address}
Subject: {subject}
Body:
{body_text}

Draft a reply following the persona, rules, and learned preferences above.
"""

DIFF_SUMMARY_PROMPT = """Compare the AI-generated draft with the user's edited version.
Summarize what the user changed in 1-2 sentences. Focus on style, tone, and content preferences.

AI DRAFT:
{draft_before}

USER'S VERSION:
{draft_after}

Summary of changes:"""


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
    print("Prompt templates OK")
