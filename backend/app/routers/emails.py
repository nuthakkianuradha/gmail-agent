from fastapi import APIRouter, Depends, Query
from app.dependencies import get_current_user
from app.services import gmail_service, auth_service
from app.models.email import InboxResponse, EmailMessage, ThreadResponse

router = APIRouter()


@router.get("/inbox", response_model=InboxResponse)
async def inbox(
    page_token: str | None = Query(None),
    max_results: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)
    result = gmail_service.list_inbox(access_token, page_token, max_results)
    return result


@router.get("/{message_id}", response_model=EmailMessage)
async def get_email(
    message_id: str,
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)
    return gmail_service.get_message(access_token, message_id)


@router.get("/thread/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)
    return gmail_service.get_thread(access_token, thread_id)


if __name__ == "__main__":
    print("Email router endpoints:")
    for route in router.routes:
        print(f"  {route.methods} {route.path}")
    print("Email router module OK")
