"""Shared FastAPI dependencies."""

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.exceptions import AuthError
from app.models import User
from app.services import auth as auth_service

bearer_scheme = HTTPBearer(auto_error=False)


class AuthContext:
    def __init__(self, user: User, payload: dict) -> None:
        self.user = user
        self.payload = payload


def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthContext:
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or not credentials.credentials.strip()
    ):
        raise AuthError("Not authenticated")
    user, payload = auth_service.authenticate_token(db, credentials.credentials)
    return AuthContext(user, payload)


def get_current_user(context: AuthContext = Depends(get_auth_context)) -> User:
    return context.user
