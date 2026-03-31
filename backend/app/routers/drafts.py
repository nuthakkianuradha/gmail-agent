from fastapi import APIRouter, Depends
from app.dependencies import get_current_user
from app.services import auth_service, gmail_service, rag_service, archive_service
from app.services.llm_service import generate_draft
from app.services.modification_service import store_modification
from app.models.draft import DraftGenerateRequest, DraftGenerateResponse, DraftSendRequest

router = APIRouter()


@router.post("/generate", response_model=DraftGenerateResponse)
async def generate(
    req: DraftGenerateRequest,
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)

    # Fetch the email to reply to
    email_data = gmail_service.get_message(access_token, req.gmail_message_id)

    # Assemble RAG prompt
    system_prompt, user_prompt, context_count = rag_service.assemble_prompt(
        user["id"], email_data
    )

    # Generate draft via LLM
    draft = await generate_draft(system_prompt, user_prompt)

    return DraftGenerateResponse(draft=draft, context_used=context_count)


@router.post("/send")
async def send(
    req: DraftSendRequest,
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)

    # Get the original message for threading headers
    original_msg = gmail_service.get_message(access_token, req.gmail_message_id)
    message_id_header = original_msg.get("message_id_header", "")

    # Send the reply
    sent = gmail_service.send_reply(
        access_token=access_token,
        to=req.to,
        subject=req.subject,
        body=req.body,
        thread_id=req.gmail_thread_id,
        message_id_header=message_id_header,
    )

    # Archive the sent email
    archive_service.archive_sent_email(
        user_id=user["id"],
        gmail_message_id=sent.get("id", ""),
        gmail_thread_id=req.gmail_thread_id,
        from_address=user["email"],
        to_address=req.to,
        subject=req.subject,
        body_text=req.body,
    )

    # If user edited the draft, store the modification
    if req.draft_before and req.draft_before != req.body:
        await store_modification(
            user_id=user["id"],
            email_id=None,
            subject=req.subject,
            snippet=original_msg.get("snippet", ""),
            draft_before=req.draft_before,
            draft_after=req.body,
        )

    return {"status": "sent", "gmail_message_id": sent.get("id", "")}


if __name__ == "__main__":
    print("Drafts router endpoints:")
    for route in router.routes:
        print(f"  {route.methods} {route.path}")
    print("Drafts router module OK")
