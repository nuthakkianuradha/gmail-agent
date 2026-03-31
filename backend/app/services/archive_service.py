from app.db.supabase_client import get_supabase
from app.services.rag_service import index_email


def archive_sent_email(
    user_id: str,
    gmail_message_id: str,
    gmail_thread_id: str,
    from_address: str,
    to_address: str,
    subject: str,
    body_text: str,
) -> dict:
    """Archive a sent email and embed it for RAG."""
    supabase = get_supabase()
    result = supabase.table("emails").upsert(
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

    # Embed the sent email
    index_email(user_id, email_record)

    return email_record


if __name__ == "__main__":
    print("Archive service:")
    print("  archive_sent_email(user_id, gmail_message_id, gmail_thread_id, from, to, subject, body)")
    print("Archive service module OK")
