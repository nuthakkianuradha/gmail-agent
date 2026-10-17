"""RAG **learning** — how memory grows after every send.

Two things are recorded when the user sends a reply:

1. ``archive_sent_email``  — the outbound email goes into the ``emails`` table
   and is indexed, so future replies can imitate it.
2. ``store_modification``  — if the user edited the AI draft, the before/after
   pair is summarized by a cheap LLM call ("what did they change?"), stored in
   ``modifications``, and indexed, so the agent stops making the same mistake.
"""

from app.core import llm
from app.core.db import get_supabase
from app.rag.indexing import index_email, index_modification

DIFF_SUMMARY_PROMPT = """Compare the AI-generated draft with the user's edited version.
Summarize what the user changed in 1-2 sentences. Focus on style, tone, and content preferences.

AI DRAFT:
{draft_before}

USER'S VERSION:
{draft_after}

Summary of changes:"""


async def summarize_diff(draft_before: str, draft_after: str) -> str:
    """One cheap LLM call describing the user's edit; never raises."""
    prompt = DIFF_SUMMARY_PROMPT.format(
        draft_before=draft_before[:1000],
        draft_after=draft_after[:1000],
    )
    try:
        return await llm.chat(prompt, summary=True, temperature=0.3, max_tokens=200)
    except Exception:
        return "User modified the draft."


def archive_sent_email(
    user_id: str,
    gmail_message_id: str,
    gmail_thread_id: str,
    from_address: str,
    to_address: str,
    subject: str,
    body_text: str,
) -> dict:
    """Persist a sent email (direction=outbound) and index it."""
    result = get_supabase().table("emails").upsert(
        {
            "user_id": user_id,
            "gmail_message_id": gmail_message_id,
            "gmail_thread_id": gmail_thread_id,
            "direction": "outbound",
            "from_address": from_address,
            "to_address": to_address,
            "subject": subject,
            "body_text": body_text,
        },
        on_conflict="user_id,gmail_message_id",
    ).execute()
    email_record = result.data[0]
    index_email(user_id, email_record)
    return email_record


async def store_modification(
    user_id: str,
    email_id: str | None,
    subject: str,
    snippet: str,
    draft_before: str,
    draft_after: str,
) -> dict:
    """Record a user edit (with an LLM diff summary) and index it."""
    diff_summary = await summarize_diff(draft_before, draft_after)

    result = get_supabase().table("modifications").insert(
        {
            "user_id": user_id,
            "email_id": email_id,
            "original_email_subject": subject,
            "original_email_snippet": snippet[:500],
            "draft_before": draft_before,
            "draft_after": draft_after,
            "diff_summary": diff_summary,
        }
    ).execute()
    modification = result.data[0]

    index_modification(
        user_id=user_id,
        modification_id=modification["id"],
        snippet=snippet[:200],
        draft_before=draft_before,
        draft_after=draft_after,
        diff_summary=diff_summary,
    )
    return modification


if __name__ == "__main__":
    print("RAG learning (feedback loop):")
    print("  archive_sent_email(user_id, gmail_message_id, gmail_thread_id, from, to, subject, body)")
    print("  store_modification(user_id, email_id, subject, snippet, before, after)  [async]")
    print("  summarize_diff(before, after) -> str  [async, cheap model]")
    print("RAG learning module OK")
