"""Drafts router — a thin HTTP adapter over the reply agent.

All the real work (RAG, prompting, LLM, Gmail-over-MCP, learning from edits)
lives in :class:`app.agent.agent.ReplyAgent`. This router only maps requests to
agent calls and shapes the response.
"""

from fastapi import APIRouter, Depends

from app.dependencies import get_current_user
from app.agent.agent import ReplyAgent
from app.models.draft import (
    DraftGenerateRequest,
    DraftGenerateResponse,
    DraftSendRequest,
)

router = APIRouter()


@router.post("/generate", response_model=DraftGenerateResponse)
async def generate(
    req: DraftGenerateRequest,
    user: dict = Depends(get_current_user),
):
    agent = ReplyAgent(user)
    output = await agent.generate_reply(req.gmail_message_id)
    return DraftGenerateResponse(draft=output.draft, context_used=output.context_used)


@router.post("/send")
async def send(
    req: DraftSendRequest,
    user: dict = Depends(get_current_user),
):
    agent = ReplyAgent(user)
    return await agent.send_reply(
        gmail_thread_id=req.gmail_thread_id,
        gmail_message_id=req.gmail_message_id,
        to=req.to,
        subject=req.subject,
        body=req.body,
        draft_before=req.draft_before,
    )


if __name__ == "__main__":
    print("Drafts router endpoints (delegate to ReplyAgent):")
    for route in router.routes:
        print(f"  {route.methods} {route.path}")
    print("Drafts router module OK")
