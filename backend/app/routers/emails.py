"""Emails router — reads Gmail exclusively through the MCP client.

The router decrypts the user's access token and hands it to
:class:`app.mcp.client.GmailMCPClient`; every Gmail read goes over the MCP
protocol to the Gmail tool server. The router never calls the Gmail SDK directly.
"""

from fastapi import APIRouter, Depends, Query

from app.dependencies import get_current_user
from app.services import auth_service
from app.mcp.client import GmailMCPClient
from app.models.email import InboxResponse, EmailMessage, ThreadResponse

router = APIRouter()


@router.get("/inbox", response_model=InboxResponse)
async def inbox(
    page_token: str | None = Query(None),
    max_results: int = Query(20, ge=1, le=50),
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)
    async with GmailMCPClient(access_token) as gmail:
        return await gmail.list_inbox(page_token, max_results)


@router.get("/{message_id}", response_model=EmailMessage)
async def get_email(
    message_id: str,
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)
    async with GmailMCPClient(access_token) as gmail:
        return await gmail.get_message(message_id)


@router.get("/thread/{thread_id}", response_model=ThreadResponse)
async def get_thread(
    thread_id: str,
    user: dict = Depends(get_current_user),
):
    access_token = auth_service.get_decrypted_access_token(user)
    async with GmailMCPClient(access_token) as gmail:
        return await gmail.get_thread(thread_id)


if __name__ == "__main__":
    print("Email router endpoints (Gmail via MCP client):")
    for route in router.routes:
        print(f"  {route.methods} {route.path}")
    print("Email router module OK")
