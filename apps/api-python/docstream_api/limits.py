"""
Usage-tier enforcement dependencies.

``get_or_create_user``
    Reconcile the JWT email with a ``User`` row — creates one on first
    interaction (lazy registration).

``require_quota``
    Gated dependency that checks the user's plan and monthly usage
    before allowing a conversion to proceed. Free-tier users are
    limited to 5 conversions per month.
"""

from __future__ import annotations

import uuid

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from docstream_api.auth import get_current_user
from docstream_api.database import get_db
from docstream_api.db_models import User

FREE_TIER_LIMIT = 5


def get_or_create_user(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Return the ``User`` row for the authenticated email, creating it if missing.

    This is a lazy-registration pattern — the first time a JWT-bearing
    request hits the API, a ``User`` record is created with ``plan="free"``
    and ``monthly_usage=0``.
    """
    email = current_user["email"]
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            plan="free",
            monthly_usage=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def require_quota(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> User:
    """Check the user's usage quota and increment the counter if allowed.

    Free-tier users get 5 conversions per month (mapped to ``monthly_usage``).
    Pro users have no limit.

    Raises ``403`` when the free-tier limit is exhausted.
    """
    if user.plan == "free" and user.monthly_usage >= FREE_TIER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free tier limit reached. Please upgrade to Pro.",
        )

    user.monthly_usage += 1
    db.commit()
    return user


__all__ = ["get_or_create_user", "require_quota", "FREE_TIER_LIMIT"]
