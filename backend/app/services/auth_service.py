from datetime import datetime, timedelta, timezone
from jose import jwt
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from app.config import get_settings
from app.utils.crypto import encrypt_token, decrypt_token
from app.db.supabase_client import get_supabase

settings = get_settings()

GOOGLE_TOKEN_URI = "https://oauth2.googleapis.com/token"

# Store pending OAuth flows keyed by state (in-memory, fine for single-server dev)
_pending_flows: dict[str, Flow] = {}


def build_oauth_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": GOOGLE_TOKEN_URI,
            "redirect_uris": [settings.google_redirect_uri],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=settings.google_scopes,
        redirect_uri=settings.google_redirect_uri,
    )
    return flow


def get_authorization_url() -> tuple[str, str]:
    flow = build_oauth_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="consent",
        include_granted_scopes="true",
    )
    # Store the flow so we can reuse it in the callback (preserves code_verifier)
    _pending_flows[state] = flow
    return auth_url, state


def exchange_code_for_tokens(code: str, state: str) -> dict:
    # Reuse the same flow that generated the auth URL (has the code_verifier)
    flow = _pending_flows.pop(state, None)
    if flow is None:
        flow = build_oauth_flow()

    flow.fetch_token(code=code)
    credentials = flow.credentials
    return {
        "access_token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
    }


def get_google_user_info(access_token: str) -> dict:
    creds = Credentials(token=access_token)
    service = build("oauth2", "v2", credentials=creds)
    return service.userinfo().get().execute()


def refresh_access_token(refresh_token: str) -> dict:
    creds = Credentials(
        token=None,
        refresh_token=refresh_token,
        token_uri=GOOGLE_TOKEN_URI,
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
    )
    creds.refresh(None)
    return {
        "access_token": creds.token,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def upsert_user(user_info: dict, tokens: dict) -> dict:
    supabase = get_supabase()
    enc_access = encrypt_token(tokens["access_token"], settings.encryption_key)
    enc_refresh = encrypt_token(tokens["refresh_token"], settings.encryption_key)

    user_data = {
        "google_id": user_info["id"],
        "email": user_info["email"],
        "name": user_info.get("name"),
        "picture_url": user_info.get("picture"),
        "access_token_encrypted": enc_access,
        "refresh_token_encrypted": enc_refresh,
        "token_expiry": tokens.get("expiry"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = (
        supabase.table("users")
        .upsert(user_data, on_conflict="google_id")
        .execute()
    )
    return result.data[0]


def create_jwt(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])


def get_user_by_id(user_id: str) -> dict | None:
    supabase = get_supabase()
    result = supabase.table("users").select("*").eq("id", user_id).execute()
    return result.data[0] if result.data else None


def get_decrypted_access_token(user: dict) -> str:
    """Get a valid access token, refreshing if expired."""
    expiry = user.get("token_expiry")
    if expiry:
        expiry_dt = datetime.fromisoformat(expiry)
        if expiry_dt < datetime.now(timezone.utc):
            refresh_token = decrypt_token(
                user["refresh_token_encrypted"], settings.encryption_key
            )
            new_tokens = refresh_access_token(refresh_token)
            supabase = get_supabase()
            enc_access = encrypt_token(
                new_tokens["access_token"], settings.encryption_key
            )
            supabase.table("users").update(
                {
                    "access_token_encrypted": enc_access,
                    "token_expiry": new_tokens["expiry"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", user["id"]).execute()
            return new_tokens["access_token"]

    return decrypt_token(user["access_token_encrypted"], settings.encryption_key)


if __name__ == "__main__":
    token = create_jwt("test-user-id", "test@gmail.com")
    print(f"JWT created: {token[:50]}...")
    decoded = decode_jwt(token)
    print(f"JWT decoded: {decoded}")
    assert decoded["sub"] == "test-user-id"
    assert decoded["email"] == "test@gmail.com"
    print("JWT round-trip OK")

    auth_url, state = get_authorization_url()
    print(f"\nOAuth URL: {auth_url[:80]}...")
    print(f"State: {state}")
    print(f"Pending flows stored: {len(_pending_flows)}")
