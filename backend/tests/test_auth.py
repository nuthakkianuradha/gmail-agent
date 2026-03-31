import pytest
from datetime import datetime, timedelta, timezone
from jose import jwt as jose_jwt
from app.services.auth_service import create_jwt, decode_jwt
from app.config import get_settings

settings = get_settings()


def test_jwt_roundtrip():
    token = create_jwt("user-123", "user@gmail.com")
    decoded = decode_jwt(token)
    assert decoded["sub"] == "user-123"
    assert decoded["email"] == "user@gmail.com"


def test_jwt_contains_expiry():
    token = create_jwt("user-123", "user@gmail.com")
    decoded = decode_jwt(token)
    assert "exp" in decoded
    assert "iat" in decoded
    # Expiry should be ~1 hour from now
    exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
    now = datetime.now(timezone.utc)
    assert timedelta(minutes=55) < (exp - now) < timedelta(minutes=65)


def test_jwt_expired_token_fails():
    payload = {
        "sub": "user-123",
        "email": "user@gmail.com",
        "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        "iat": datetime.now(timezone.utc) - timedelta(hours=2),
    }
    token = jose_jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    with pytest.raises(Exception):
        decode_jwt(token)


def test_jwt_wrong_secret_fails():
    token = create_jwt("user-123", "user@gmail.com")
    with pytest.raises(Exception):
        jose_jwt.decode(token, "wrong-secret", algorithms=["HS256"])


def test_jwt_different_users_different_tokens():
    t1 = create_jwt("user-1", "a@gmail.com")
    t2 = create_jwt("user-2", "b@gmail.com")
    assert t1 != t2
