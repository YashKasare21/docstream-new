"""
Auth dependency — validates NextAuth-issued JWTs signed with HS256.

Every protected endpoint injects ``get_current_user`` which reads the
``Authorization: Bearer <token>`` header, decodes the JWT using the
shared ``NEXTAUTH_SECRET``, and returns the caller's email.

Usage::

    from docstream_api.auth import get_current_user

    @router.get("/api/v2/jobs")
    def list_jobs(current_user: dict = Depends(get_current_user)):
        email = current_user["email"]
        ...
"""

from __future__ import annotations

import logging
import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_security_scheme),
) -> dict:
    """Extract and validate the JWT from the ``Authorization`` header.

    Returns a dict with at least an ``email`` key on success.

    Raises ``HTTPException(401)`` when the token is missing, expired, or
    otherwise invalid.
    """
    if credentials is None:
        logger.warning("Auth: no credentials (Authorization header missing)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    secret = os.environ.get("NEXTAUTH_SECRET")
    logger.info(f"NEXTAUTH_SECRET present: {bool(secret)}")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: NEXTAUTH_SECRET not set",
        )

    logger.info(f"Auth: token starts with: {credentials.credentials[:20]}...")

    try:
        payload = jwt.decode(
            credentials.credentials,
            secret,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        logger.warning("Auth: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError as e:
        logger.warning(f"Auth: invalid token — {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    email = payload.get("email")
    if not email:
        logger.warning("Auth: token missing email claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing email claim",
        )

    logger.info(f"Auth: authenticated as {email}")
    return {"email": email}


__all__ = ["get_current_user"]
