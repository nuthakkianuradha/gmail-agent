from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from app.dependencies import get_current_user
from app.db.supabase_client import get_supabase
from app.services.rag_service import index_rule, index_persona
from app.models.persona import PersonaRequest, PersonaResponse, RuleRequest, RuleResponse

router = APIRouter()


@router.get("/persona", response_model=PersonaResponse | None)
async def get_persona(user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = supabase.table("personas").select("*").eq("user_id", user["id"]).execute()
    if not result.data:
        return None
    return result.data[0]


@router.put("/persona", response_model=PersonaResponse)
async def save_persona(
    req: PersonaRequest,
    user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    data = {
        "user_id": user["id"],
        "display_name": req.display_name,
        "tone": req.tone,
        "style_notes": req.style_notes,
        "signature": req.signature,
        "language": req.language,
        "custom_instructions": req.custom_instructions,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = supabase.table("personas").upsert(data, on_conflict="user_id").execute()
    persona = result.data[0]

    # Embed persona for RAG
    index_persona(user["id"], persona["id"], persona)

    return persona


@router.get("/rules", response_model=list[RuleResponse])
async def list_rules(user: dict = Depends(get_current_user)):
    supabase = get_supabase()
    result = (
        supabase.table("rules")
        .select("*")
        .eq("user_id", user["id"])
        .order("created_at")
        .execute()
    )
    return result.data or []


@router.post("/rules", response_model=RuleResponse)
async def create_rule(
    req: RuleRequest,
    user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = supabase.table("rules").insert(
        {
            "user_id": user["id"],
            "rule_text": req.rule_text,
            "category": req.category,
        }
    ).execute()
    rule = result.data[0]

    # Embed rule for RAG
    index_rule(user["id"], rule["id"], rule["rule_text"])

    return rule


@router.put("/rules/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: str,
    req: RuleRequest,
    user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    result = (
        supabase.table("rules")
        .update({"rule_text": req.rule_text, "category": req.category})
        .eq("id", rule_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule = result.data[0]
    index_rule(user["id"], rule["id"], rule["rule_text"])
    return rule


@router.delete("/rules/{rule_id}")
async def delete_rule(
    rule_id: str,
    user: dict = Depends(get_current_user),
):
    supabase = get_supabase()
    # Delete the rule
    supabase.table("rules").delete().eq("id", rule_id).eq("user_id", user["id"]).execute()
    # Clean up embedding
    supabase.table("embeddings").delete().eq("source_id", rule_id).eq("user_id", user["id"]).execute()
    return {"status": "deleted"}


if __name__ == "__main__":
    print("Settings router endpoints:")
    for route in router.routes:
        print(f"  {route.methods} {route.path}")
    print("Settings router module OK")
