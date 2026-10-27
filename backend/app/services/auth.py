"""Login checks and token revocation."""

from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.exceptions import AuthError
from app.models import RevokedToken, User
from app.security import decode_token, dummy_verify, verify_password


def authenticate(db: Session, username: str, password: str) -> User | None:
    user = db.query(User).filter(User.username == username).one_or_none()
    if user is None:
        dummy_verify(password)
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def authenticate_token(db: Session, token: str) -> tuple[User, dict]:
    payload = decode_token(token)
    if db.get(RevokedToken, payload["jti"]) is not None:
        raise AuthError("Token has been revoked")
    user = db.query(User).filter(User.username == payload["sub"]).one_or_none()
    if user is None:
        raise AuthError("Could not validate credentials")
    return user, payload


def revoke_token(db: Session, jti: str, expires_at: int) -> None:
    now = datetime.now(timezone.utc)
    db.query(RevokedToken).filter(RevokedToken.expires_at < now).delete(synchronize_session=False)
    if db.get(RevokedToken, jti) is None:
        db.add(
            RevokedToken(
                jti=jti,
                expires_at=datetime.fromtimestamp(int(expires_at), tz=timezone.utc),
            )
        )
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
