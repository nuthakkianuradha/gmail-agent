from pydantic import BaseModel
from datetime import datetime


class EmailMessage(BaseModel):
    gmail_message_id: str
    gmail_thread_id: str
    from_address: str
    to_address: str
    subject: str
    body_text: str
    body_html: str | None = None
    snippet: str = ""
    labels: list[str] = []
    received_at: str | None = None


class EmailSummary(BaseModel):
    gmail_message_id: str
    gmail_thread_id: str
    from_address: str
    to_address: str
    subject: str
    snippet: str
    labels: list[str] = []
    received_at: str | None = None
    is_unread: bool = False


class ThreadResponse(BaseModel):
    thread_id: str
    messages: list[EmailMessage]


class InboxResponse(BaseModel):
    emails: list[EmailSummary]
    next_page_token: str | None = None


if __name__ == "__main__":
    email = EmailSummary(
        gmail_message_id="msg-123",
        gmail_thread_id="thread-456",
        from_address="sender@gmail.com",
        to_address="me@gmail.com",
        subject="Test Email",
        snippet="Hey, this is a test...",
        labels=["INBOX", "CATEGORY_PRIMARY"],
        is_unread=True,
    )
    print(f"EmailSummary: {email.model_dump_json(indent=2)}")
