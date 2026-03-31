from pydantic import BaseModel


class DraftGenerateRequest(BaseModel):
    gmail_message_id: str
    gmail_thread_id: str


class DraftGenerateResponse(BaseModel):
    draft: str
    context_used: int


class DraftSendRequest(BaseModel):
    gmail_thread_id: str
    gmail_message_id: str
    to: str
    subject: str
    body: str
    draft_before: str | None = None  # Original AI draft, if user edited


if __name__ == "__main__":
    req = DraftGenerateRequest(gmail_message_id="msg-1", gmail_thread_id="thread-1")
    print(f"DraftGenerateRequest: {req.model_dump_json()}")

    resp = DraftGenerateResponse(draft="Hi, thanks for your email...", context_used=5)
    print(f"DraftGenerateResponse: {resp.model_dump_json()}")

    send = DraftSendRequest(
        gmail_thread_id="thread-1",
        gmail_message_id="msg-1",
        to="user@example.com",
        subject="Re: Hello",
        body="Thanks for reaching out!",
        draft_before="Thank you for reaching out!",
    )
    print(f"DraftSendRequest: {send.model_dump_json()}")
    print("Draft models OK")
