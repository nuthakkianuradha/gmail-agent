from cryptography.fernet import Fernet


def get_fernet(encryption_key: str) -> Fernet:
    return Fernet(encryption_key.encode())


def encrypt_token(token: str, encryption_key: str) -> str:
    f = get_fernet(encryption_key)
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str, encryption_key: str) -> str:
    f = get_fernet(encryption_key)
    return f.decrypt(encrypted_token.encode()).decode()


if __name__ == "__main__":
    # Generate a key and test encrypt/decrypt round-trip
    key = Fernet.generate_key().decode()
    print(f"Generated Fernet key: {key}")

    test_token = "ya29.some-google-access-token-here"
    encrypted = encrypt_token(test_token, key)
    print(f"Encrypted: {encrypted[:50]}...")

    decrypted = decrypt_token(encrypted, key)
    print(f"Decrypted: {decrypted}")
    assert decrypted == test_token
    print("Round-trip OK")
