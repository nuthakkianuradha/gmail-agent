from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Supabase
    supabase_url: str
    supabase_service_key: str

    # LLM provider selection.
    #   local = Ollama (or any OpenAI-compatible local server) is the primary;
    #           Groq / OpenRouter are used as fallbacks only if their keys are set.
    #   groq  = Groq is the primary, OpenRouter the fallback (cloud mode).
    llm_provider: Literal["local", "groq"] = "local"
    local_llm_base_url: str = "http://localhost:11434/v1"
    local_llm_model: str = "llama3.1:8b"
    # Cheap model for "what did the user change?" summaries. Empty = same as
    # local_llm_model.
    local_llm_summary_model: str = ""

    # Cloud LLM keys — optional. Empty means that provider is skipped.
    groq_api_key: str = ""
    openrouter_api_key: str = ""

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
    print(f"  LLM provider: {settings.llm_provider}")
    if settings.llm_provider == "local":
        print(f"  Local LLM: {settings.local_llm_model} @ {settings.local_llm_base_url}")
    print(f"  Groq key: {'set' if settings.groq_api_key else 'not set'}")
    print(f"  OpenRouter key: {'set' if settings.openrouter_api_key else 'not set'}")
    print(f"  Scopes: {len(settings.google_scopes)} configured")
