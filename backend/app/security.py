"""
Signed-session authentication.

Clients send `Authorization: Bearer <jwt>`. `AuthMiddleware` verifies the token and then *overwrites* the
`X-User-ID` request header with the verified user id (any client-supplied value is discarded), so existing
handlers that read `X-User-ID` can no longer be spoofed. Tokens are issued by Google login and by the
guest endpoint. Protected paths without a valid token get 401.

Env: JWT_SECRET (required in production), JWT_TTL_DAYS (default 30).
"""

import logging
import os
import secrets
import time
from typing import Optional

import jwt
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

_ALGORITHM = "HS256"
_secret: Optional[str] = None


def _get_secret() -> str:
    global _secret
    if _secret is None:
        _secret = os.getenv("JWT_SECRET", "")
        if len(_secret) < 16:
            _secret = secrets.token_urlsafe(32)
            logger.warning("JWT_SECRET not set (or < 16 chars): using an ephemeral secret. "
                           "Sessions will be invalidated on restart. Set JWT_SECRET in .env.")
    return _secret


def create_access_token(user_id: str, ttl_days: Optional[int] = None) -> str:
    days = ttl_days if ttl_days is not None else int(os.getenv("JWT_TTL_DAYS", "30"))
    now = int(time.time())
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": now + days * 86400}, _get_secret(), algorithm=_ALGORITHM)


def verify_access_token(token: str) -> Optional[str]:
    """Return the user id for a valid, unexpired token, else None."""
    try:
        payload = jwt.decode(token, _get_secret(), algorithms=[_ALGORITHM], options={"require": ["sub", "exp"]})
        return str(payload["sub"])
    except jwt.PyJWTError:
        return None


# Paths (relative to the /api mount) reachable without a token.
PUBLIC_EXACT = {
    "/auth/google-login",
    "/user/guest",
    "/user/get_id",
    "/metrics/track",
    "/metrics/site-metric",
    "/openapi.json",
}
# "/data/cached_pdfs/uploads/": browsers can't attach a Bearer header to <iframe>/<a> PDF loads; files use unguessable uuid4 names.
PUBLIC_PREFIXES = ("/papers", "/search", "/search-summary", "/docs", "/data/cached_pdfs/uploads")


def _is_public(path: str) -> bool:
    path = path.rstrip("/") or "/"
    return path in PUBLIC_EXACT or any(path == p or path.startswith(p + "/") for p in PUBLIC_PREFIXES)


class AuthMiddleware:
    """Pure ASGI middleware (no body buffering, safe for streaming responses)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] == "OPTIONS":
            await self.app(scope, receive, send)
            return

        headers = [(k, v) for k, v in scope["headers"] if k.lower() != b"x-user-id"]  # never trust client value
        user_id = None
        for k, v in scope["headers"]:
            if k.lower() == b"authorization":
                value = v.decode("latin-1")
                if value.lower().startswith("bearer "):
                    user_id = verify_access_token(value[7:].strip())
                break

        if user_id:
            headers.append((b"x-user-id", user_id.encode()))
        else:
            path = scope["path"]
            root = scope.get("root_path", "")
            if root and path.startswith(root):
                path = path[len(root):]
            if not _is_public(path):
                resp = JSONResponse({"detail": "Authentication required"}, status_code=401,
                                    headers={"WWW-Authenticate": "Bearer"})
                await resp(scope, receive, send)
                return

        scope = dict(scope)
        scope["headers"] = headers
        await self.app(scope, receive, send)
