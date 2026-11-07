from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_roundtrip():
    hashed = hash_password("sup3r-secret")
    assert hashed != "sup3r-secret"
    assert verify_password("sup3r-secret", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_roundtrip():
    import uuid

    token = create_access_token(uuid.uuid4(), 3)
    payload = decode_access_token(token)
    assert payload["type"] == "access"
    assert payload["tv"] == 3


def test_secret_encryption_roundtrip():
    ciphertext = encrypt_secret("sk-test-secret")
    assert "sk-test-secret" not in ciphertext
    assert decrypt_secret(ciphertext) == "sk-test-secret"
