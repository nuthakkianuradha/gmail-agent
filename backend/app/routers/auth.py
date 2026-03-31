from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from app.services import auth_service
from app.dependencies import get_current_user
from app.config import get_settings
from app.models.user import UserProfile

router = APIRouter()
settings = get_settings()


@router.get("/login")
async def login():
    auth_url, state = auth_service.get_authorization_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def callback(code: str, state: str | None = None):
    try:
        tokens = auth_service.exchange_code_for_tokens(code, state or "")
        user_info = auth_service.get_google_user_info(tokens["access_token"])
        user = auth_service.upsert_user(user_info, tokens)
        jwt_token = auth_service.create_jwt(user["id"], user["email"])
        redirect_url = f"{settings.frontend_url}/auth/callback?token={jwt_token}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {str(e)}")


@router.get("/me", response_model=UserProfile)
async def me(user: dict = Depends(get_current_user)):
    return UserProfile(
        id=user["id"],
        email=user["email"],
        name=user.get("name"),
        picture_url=user.get("picture_url"),
    )


if __name__ == "__main__":
    print("Auth router endpoints:")
    for route in router.routes:
        print(f"  {route.methods} {route.path}")
    print("Auth router module OK")
