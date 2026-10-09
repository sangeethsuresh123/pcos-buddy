"""FastAPI dependencies for authentication."""

from fastapi import Cookie, Header, HTTPException, status

from backend.auth import store
from backend.config import settings


def _token_from_request(authorization: str | None, cookie: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return cookie


def get_current_user(
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
) -> dict:
    token = _token_from_request(authorization, session_cookie)
    user = store.get_user_by_token(token) if token else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
