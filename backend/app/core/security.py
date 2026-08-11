import hashlib
import secrets
from datetime import timedelta
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings
from app.core.time import utcnow

password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_token(subject: str, token_type: str, lifetime: timedelta) -> tuple[str, str]:
    settings = get_settings()
    now = utcnow()
    token_id = str(uuid4())
    payload = {
        "sub": subject,
        "type": token_type,
        "jti": token_id,
        "iat": now,
        "exp": now + lifetime,
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256"), token_id


def decode_token(token: str, expected_type: str) -> dict:
    settings = get_settings()
    payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload


def random_export_token() -> str:
    return secrets.token_urlsafe(24)
