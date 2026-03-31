import pytest
from cryptography.fernet import Fernet
from app.utils.crypto import encrypt_token, decrypt_token


@pytest.fixture
def fernet_key():
    return Fernet.generate_key().decode()


def test_encrypt_decrypt_roundtrip(fernet_key):
    token = "ya29.some-google-access-token"
    encrypted = encrypt_token(token, fernet_key)
    assert encrypted != token
    decrypted = decrypt_token(encrypted, fernet_key)
    assert decrypted == token


def test_different_tokens_produce_different_ciphertexts(fernet_key):
    enc1 = encrypt_token("token-one", fernet_key)
    enc2 = encrypt_token("token-two", fernet_key)
    assert enc1 != enc2


def test_same_token_produces_different_ciphertexts(fernet_key):
    """Fernet uses a random IV, so encrypting the same value twice gives different results."""
    enc1 = encrypt_token("same-token", fernet_key)
    enc2 = encrypt_token("same-token", fernet_key)
    assert enc1 != enc2
    assert decrypt_token(enc1, fernet_key) == decrypt_token(enc2, fernet_key)


def test_wrong_key_fails():
    key1 = Fernet.generate_key().decode()
    key2 = Fernet.generate_key().decode()
    encrypted = encrypt_token("secret", key1)
    with pytest.raises(Exception):
        decrypt_token(encrypted, key2)


def test_empty_token(fernet_key):
    encrypted = encrypt_token("", fernet_key)
    assert decrypt_token(encrypted, fernet_key) == ""
