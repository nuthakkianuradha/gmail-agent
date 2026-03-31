from supabase import create_client, Client
from functools import lru_cache
from app.config import get_settings


@lru_cache
def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


if __name__ == "__main__":
    client = get_supabase()
    print(f"Supabase client created: {type(client).__name__}")
    # Quick health check — list tables via a simple query
    try:
        result = client.table("users").select("id").limit(1).execute()
        print(f"Connected OK. Users table accessible: {len(result.data)} rows returned")
    except Exception as e:
        print(f"Connection test: {e}")
        print("(This is expected if the users table doesn't exist yet)")
