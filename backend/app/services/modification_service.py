from app.db.supabase_client import get_supabase
from app.services.llm_service import summarize_diff
from app.services.rag_service import index_modification


async def store_modification(
    user_id: str,
    email_id: str | None,
    subject: str,
    snippet: str,
    draft_before: str,
    draft_after: str,
) -> dict:
    """Store a user's edit and embed it for future RAG retrieval."""
    # Generate diff summary via LLM
    diff_summary = await summarize_diff(draft_before, draft_after)

    supabase = get_supabase()
    result = supabase.table("modifications").insert(
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

    # Embed the modification for future retrieval
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
    print("Modification service:")
    print("  store_modification(user_id, email_id, subject, snippet, before, after)")
    print("Modification service module OK")
