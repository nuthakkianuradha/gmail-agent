from pydantic import BaseModel
from datetime import datetime


class UserProfile(BaseModel):
    id: str
    email: str
    name: str | None = None
    picture_url: str | None = None


class UserInDB(BaseModel):
    id: str
    google_id: str
    email: str
    name: str | None = None
    picture_url: str | None = None
    access_token_encrypted: str
    refresh_token_encrypted: str
    token_expiry: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


if __name__ == "__main__":
    user = UserProfile(id="test-123", email="test@gmail.com", name="Test User")
    print(f"UserProfile: {user.model_dump_json(indent=2)}")

    user_db = UserInDB(
        id="test-123",
        google_id="google-456",
        email="test@gmail.com",
        name="Test User",
        access_token_encrypted="encrypted...",
        refresh_token_encrypted="encrypted...",
    )
    print(f"UserInDB: {user_db.model_dump_json(indent=2)}")
