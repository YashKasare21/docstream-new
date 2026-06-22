"""
Usage-tier enforcement dependencies.

``get_or_create_user``
    Reconcile the JWT email with a ``User`` row — creates one on first
    interaction (lazy registration).

``require_quota``
    Gated dependency that checks the user's plan and monthly usage
    before allowing a conversion to proceed. Uses the ``Usage`` model
    for tracking monthly conversions against plan-specific limits
    (5 for free, 100 for pro). Does NOT increment — that happens in
    ``increment_usage`` after a successful conversion.

``increment_usage``
    Increments the user's monthly conversion count after a successful
    conversion.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import Depends
from sqlalchemy.orm import Session

from docstream_api.auth import get_current_user
from docstream_api.database import get_db
from docstream_api.db_models import Usage, User


class QuotaExceeded(Exception):
    """Raised when the user has exhausted their monthly conversion quota."""

    def __init__(self, error: str, checkout_url: str | None = None) -> None:
        self.error = error
        self.checkout_url = checkout_url

FREE_TIER_LIMIT = 5
PRO_TIER_LIMIT = 100


def get_or_create_user(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> User:
    """Return the ``User`` row for the authenticated email, creating it if missing."""
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


def _get_or_create_usage(user_id: str, db: Session) -> Usage:
    """Get or create a Usage record for the current month."""
    now = datetime.now(timezone.utc)
    month = f"{now.year}-{now.month:02d}"
    usage = db.query(Usage).filter(Usage.user_id == user_id, Usage.month == month).first()
    if usage is None:
        usage = Usage(
            user_id=user_id,
            month=month,
            conversions_used=0,
            conversions_limit=FREE_TIER_LIMIT,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def require_quota(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> User:
    """Check the user's usage quota (does NOT increment).

    Free-tier users get 5 conversions per month.
    Pro users get 100 conversions per month.

    Raises ``403`` when the limit is exhausted with a checkout_url hint.
    """
    usage = _get_or_create_usage(user.id, db)

    limit = usage.conversions_limit
    if usage.conversions_used >= limit:
        if user.plan == "free":
            raise QuotaExceeded(
                error="Free plan limit reached. Upgrade to Pro.",
                checkout_url="/api/v2/billing/checkout",
            )
        raise QuotaExceeded(error="Pro plan limit reached.")

    return user


def increment_usage(user: User, db: Session) -> None:
    """Increment the monthly conversion counter after a successful conversion."""
    usage = _get_or_create_usage(user.id, db)
    usage.conversions_used += 1
    db.commit()


__all__ = ["get_or_create_user", "require_quota", "increment_usage", "QuotaExceeded", "FREE_TIER_LIMIT", "PRO_TIER_LIMIT"]
