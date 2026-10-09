"""Google OAuth 2.0 authorization-code flow (server side).

The redirect URI comes exclusively from ``GOOGLE_REDIRECT_URI`` and is used
verbatim for both the authorization request and the token exchange, so it
always matches the URI registered in the Google Cloud Console. Nothing here is
derived from the incoming request, which eliminates host/port mismatch bugs.
"""

from urllib.parse import urlencode, urlparse

import httpx

from backend.config import settings

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://openidconnect.googleapis.com/v1/userinfo"

_TIMEOUT = httpx.Timeout(10.0)


def is_configured() -> bool:
    return bool(
        settings.google_client_id
        and settings.google_client_secret
        and settings.google_redirect_uri
    )


def redirect_uri() -> str:
    return settings.google_redirect_uri


def oauth_origin() -> str:
    parsed = urlparse(settings.google_redirect_uri)
    return f"{parsed.scheme}://{parsed.netloc}"


def build_authorization_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
        "include_granted_scopes": "true",
    }
    return f"{AUTH_ENDPOINT}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    data = {
        "code": code,
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "redirect_uri": settings.google_redirect_uri,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.post(TOKEN_ENDPOINT, data=data)
    if res.status_code != 200:
        raise RuntimeError(f"token exchange failed ({res.status_code}): {res.text}")
    return res.json()


async def fetch_userinfo(access_token: str) -> dict:
    headers = {"Authorization": f"Bearer {access_token}"}
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        res = await client.get(USERINFO_ENDPOINT, headers=headers)
    if res.status_code != 200:
        raise RuntimeError(f"userinfo lookup failed ({res.status_code}): {res.text}")
    return res.json()