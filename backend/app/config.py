from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # LLMs
    groq_api_key: str
    openrouter_api_key: str

    # Security
    jwt_secret: str
    encryption_key: str

    # App URLs
    frontend_url: str = "http://localhost:5173"
    backend_url: str = "http://localhost:8000"

    # MCP tool server. Leave unset to run the Gmail MCP server in-process
    # (default, single deployment). Set to a base URL (e.g. the same backend or
    # a dedicated service) to reach a remotely-deployed MCP server over HTTP.
    mcp_server_url: str | None = None

    # Google OAuth scopes
    google_scopes: list[str] = [
        "openid",
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/userinfo.profile",
    ]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    settings = get_settings()
    print("Config loaded successfully:")
    print(f"  Frontend URL: {settings.frontend_url}")
    print(f"  Backend URL: {settings.backend_url}")
    print(f"  Supabase URL: {settings.supabase_url[:30]}...")
    print(f"  Google Client ID: {settings.google_client_id[:20]}...")
    print(f"  Scopes: {len(settings.google_scopes)} configured")
