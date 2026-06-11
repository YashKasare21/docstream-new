"""
Usage-tier enforcement dependencies.

``get_or_create_user``
    Reconcile the JWT email with a ``User`` row — creates one on first
    interaction (lazy registration).

``require_quota``
    Gated dependency that checks the user's plan and monthly usage
    before allowing a conversion to proceed. Free-tier users are
    limited to 5 conversions per month.

    **Monthly reset**: before checking the quota, ``require_quota``
    checks whether ``user.last_reset_date`` is from a previous calendar
    month. If so, ``monthly_usage`` is reset to 0 and the reset date
    is updated so free users get their 5 conversions back at the start
    of each month without needing a cron job.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

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


def _reset_usage_if_new_month(user: User, db: Session) -> None:
    """Reset ``monthly_usage`` to 0 if the last reset was in a previous calendar month."""
    now = datetime.now(timezone.utc)
    if user.last_reset_date is None:
        # First-time init for rows created before the column existed.
        user.last_reset_date = now
        user.monthly_usage = 0
        db.commit()
        return

    # Compare year/month — if they differ, a new month has started.
    if (user.last_reset_date.year, user.last_reset_date.month) != (now.year, now.month):
        user.monthly_usage = 0
        user.last_reset_date = now
        db.commit()


def require_quota(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> User:
    """Check the user's usage quota and increment the counter if allowed.

    Free-tier users get 5 conversions per month (mapped to ``monthly_usage``).
    Pro users have no limit.

    Before checking, resets usage if a new calendar month has started.

    Raises ``403`` when the free-tier limit is exhausted.
    """
    # Monthly reset: check if the last reset was in a previous month.
    _reset_usage_if_new_month(user, db)

    if user.plan == "free" and user.monthly_usage >= FREE_TIER_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Free tier limit reached. Please upgrade to Pro.",
        )

    user.monthly_usage += 1
    db.commit()
    return user


__all__ = ["get_or_create_user", "require_quota", "FREE_TIER_LIMIT"]
