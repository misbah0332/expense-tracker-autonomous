"""Login, logout, and the current account."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import AuthContext, get_auth_context, get_current_user
from app.exceptions import AuthError
from app.models import User
from app.schemas import LoginRequest, TokenResponse, UserRead
from app.security import create_access_token
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate(db, body.username, body.password)
    if user is None:
        raise AuthError("Invalid username or password")
    token, expires_in = create_access_token(user.username)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/logout", status_code=204)
def logout(
    context: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
) -> Response:
    auth_service.revoke_token(db, context.payload["jti"], int(context.payload["exp"]))
    return Response(status_code=204)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
