import logging
import re
import secrets
from urllib.parse import quote, unquote

from fastapi import (
    APIRouter,
    Cookie,
    Depends,
    Header,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, field_validator

from backend.auth import google, store
from backend.auth.deps import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

logger = logging.getLogger("pcos.auth")

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_STATE_COOKIE = "pcos_oauth_state"
_NEXT_COOKIE = "pcos_oauth_next"


class Credentials(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL_RE.match(value):
            raise ValueError("a valid email address is required")
        return value

    @field_validator("password")
    @classmethod
    def valid_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("password must be at least 8 characters")
        if len(value) > 128:
            raise ValueError("password must be at most 128 characters")
        return value


class UserOut(BaseModel):
    id: int
    email: str
    created_at: str


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.session_ttl_days * 24 * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=settings.auth_cookie_name, path="/")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(request: Credentials, response: Response):
    try:
        user = store.create_user(request.email, request.password)
    except store.EmailAlreadyRegistered:
        raise HTTPException(status_code=409, detail="Email already registered")
    _set_session_cookie(response, store.create_session(user["id"]))
    return UserOut(**user)


@router.post("/login", response_model=UserOut)
async def login(request: Credentials, response: Response):
    user = store.authenticate(request.email, request.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    _set_session_cookie(response, store.create_session(user["id"]))
    return UserOut(**user)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    response: Response,
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=settings.auth_cookie_name),
):
    token = authorization[7:].strip() if authorization and authorization.lower().startswith(
        "bearer "
    ) else session_cookie
    if token:
        store.delete_session(token)
    _clear_session_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    return UserOut(**user)


class AuthConfigOut(BaseModel):
    google_enabled: bool
    google_login_url: str | None = None


def _safe_next(value: str | None) -> str:
    if not value or not value.startswith("/") or value.startswith("//"):
        return "/"
    return value


def _oauth_failure(reason: str = "unknown") -> RedirectResponse:
    logger.warning("Google OAuth redirect to /login failed: %s", reason)
    response = RedirectResponse(f"/login?error=google&reason={quote(reason)}", status_code=302)
    response.delete_cookie(_STATE_COOKIE, path="/")
    response.delete_cookie(_NEXT_COOKIE, path="/")
    return response


@router.get("/config", response_model=AuthConfigOut)
async def auth_config():
    enabled = google.is_configured()
    return AuthConfigOut(
        google_enabled=enabled,
        google_login_url=google.oauth_origin() + "/api/auth/google/login" if enabled else None,
    )


@router.get("/google/login")
async def google_login(redirect: str = Query("/")):
    if not google.is_configured():
        raise HTTPException(status_code=503, detail="Google login is not configured")

    state = secrets.token_urlsafe(24)
    response = RedirectResponse(google.build_authorization_url(state), status_code=302)
    cookie_opts = {
        "max_age": 600,
        "httponly": True,
        "samesite": "lax",
        "secure": settings.cookie_secure,
        "path": "/",
    }
    response.set_cookie(_STATE_COOKIE, state, **cookie_opts)
    response.set_cookie(_NEXT_COOKIE, quote(_safe_next(redirect), safe=""), **cookie_opts)
    return response


@router.get("/google/callback")
async def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    state_cookie: str | None = Cookie(default=None, alias=_STATE_COOKIE),
    next_cookie: str | None = Cookie(default=None, alias=_NEXT_COOKIE),
):
    if error or not code or not state or not state_cookie or state != state_cookie:
        return _oauth_failure("state_mismatch")

    try:
        tokens = await google.exchange_code(code)
    except Exception as exc:
        return _oauth_failure(f"token_exchange:{exc}")

    try:
        info = await google.fetch_userinfo(tokens["access_token"])
    except Exception as exc:
        return _oauth_failure(f"userinfo:{exc}")

    email = info.get("email")
    google_id = info.get("sub")
    if not email or not google_id or not info.get("email_verified", False):
        return _oauth_failure(f"invalid_userinfo: {info}")

    user = store.get_or_create_google_user(email, google_id)
    response = RedirectResponse(_safe_next(unquote(next_cookie or "")), status_code=302)
    _set_session_cookie(response, store.create_session(user["id"]))
    response.delete_cookie(_STATE_COOKIE, path="/")
    response.delete_cookie(_NEXT_COOKIE, path="/")
    return response