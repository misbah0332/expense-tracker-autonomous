"""Password hashing and signed bearer tokens."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import bcrypt
import jwt

from app.config import get_settings
from app.exceptions import AuthError

_DUMMY_HASH = bcrypt.hashpw(b"dummy-password-not-used", bcrypt.gensalt()).decode("utf-8")


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        raise ValueError("password must be at most 72 bytes")
    return bcrypt.hashpw(password_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        return False
    try:
        return bcrypt.checkpw(password_bytes, password_hash.encode("utf-8"))
    except ValueError:
        return False


def dummy_verify(password: str) -> None:
    """Spend a comparable amount of time when the username does not exist."""
    verify_password(password, _DUMMY_HASH)


def create_access_token(subject: str, expires_delta: timedelta | None = None) -> tuple[str, int]:
    settings = get_settings()
    lifetime = expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    now = datetime.now(timezone.utc)
    expires_at = now + lifetime
    payload = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": expires_at,
        "jti": str(uuid4()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, max(int(lifetime.total_seconds()), 0)


def decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            leeway=10,
            options={"require": ["exp", "sub", "jti", "iat"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise AuthError("Could not validate credentials") from exc

    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        raise AuthError("Could not validate credentials")
    if not isinstance(payload.get("jti"), str) or not payload["jti"]:
        raise AuthError("Could not validate credentials")
    return payload
