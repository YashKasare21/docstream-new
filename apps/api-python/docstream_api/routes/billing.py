"""
Stripe billing endpoints for DocStream v2.0.

Provides plan listing, subscription status, checkout session creation,
Stripe webhook handling, and customer portal access.
"""

from __future__ import annotations

import logging
import os
import traceback
from datetime import datetime, timezone

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from docstream_api.database import SessionLocal, get_db
from docstream_api.db_models import Subscription, Usage, User
from docstream_api.limits import get_or_create_user

logger = logging.getLogger(__name__)

router = APIRouter()


def _stripe_secret() -> str:
    secret = os.environ.get("STRIPE_SECRET_KEY")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: STRIPE_SECRET_KEY not set",
        )
    return secret


def _pro_price_id() -> str:
    price_id = os.environ.get("STRIPE_PRO_PRICE_ID")
    if not price_id:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server misconfiguration: STRIPE_PRO_PRICE_ID not set",
        )
    return price_id


def _extract_stripe_id(value: object) -> str | None:
    """Extract a Stripe ID string from a field that may be a string or a StripeObject.

    In Stripe SDK v9+, expandable fields (like ``customer``, ``subscription``)
    can be returned as ``StripeObject`` instances from webhook events instead
    of plain strings, depending on the account's API version.
    StripeObject does **not** inherit from ``dict`` in v9+, so we use
    ``hasattr`` for duck-typing.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    # StripeObject (v9+) — not a dict subclass, use hasattr
    if hasattr(value, "id"):
        raw = value.id  # type: ignore[union-attr]
        return str(raw) if raw else None
    # Fallback for plain dicts
    if isinstance(value, dict):
        raw = value.get("id")
        return str(raw) if raw else None
    return str(value)


def _get_or_create_usage_record(user_id: str, db: Session) -> Usage:
    """Get or create a Usage record for the current month."""
    now = datetime.now(timezone.utc)
    month = f"{now.year}-{now.month:02d}"
    usage = db.query(Usage).filter(Usage.user_id == user_id, Usage.month == month).first()
    if usage is None:
        usage = Usage(
            user_id=user_id,
            month=month,
            conversions_used=0,
            conversions_limit=5,
        )
        db.add(usage)
        db.commit()
        db.refresh(usage)
    return usage


def _get_or_create_subscription(user_id: str, db: Session) -> Subscription:
    """Get or create a Subscription record for the user."""
    sub = db.query(Subscription).filter(Subscription.user_id == user_id).first()
    if sub is None:
        sub = Subscription(
            user_id=user_id,
            plan="free",
            status="active",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
    return sub


def _handle_checkout_completed(event: object) -> None:
    """Process a checkout.session.completed event.

    Looks up the user by ``stripe_customer_id`` and upgrades them to Pro.
    Falls back to looking up by email if the customer ID doesn't match any user.
    """
    session = event["data"]["object"]  # type: ignore[index]

    customer_id = _extract_stripe_id(session.customer)
    subscription_id = _extract_stripe_id(session.subscription)

    logger.info(
        "checkout.session.completed: customer=%s subscription=%s",
        customer_id,
        subscription_id,
    )

    if not customer_id:
        logger.warning("checkout.session.completed: no customer_id in session")
        return

    with SessionLocal() as db:
        # Try lookup by stripe_customer_id first
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()

        # Fallback: if the stripe_customer_id wasn't saved on the User row
        # (e.g. due to a race condition that created duplicate customers),
        # try to find the customer's email from Stripe and match by email.
        if user is None:
            logger.warning(
                "checkout.session.completed: no user found for stripe_customer_id=%s, "
                "falling back to Stripe customer lookup",
                customer_id,
            )
            try:
                stripe.api_key = _stripe_secret()
                stripe_customer = stripe.Customer.retrieve(customer_id)
                customer_email = stripe_customer.email
                if customer_email:
                    user = db.query(User).filter(User.email == customer_email).first()
                    if user:
                        logger.info(
                            "Found user by email=%s, updating stripe_customer_id=%s",
                            customer_email,
                            customer_id,
                        )
                        user.stripe_customer_id = customer_id
            except Exception as exc:
                logger.error("Failed to retrieve Stripe customer %s: %s", customer_id, exc)
                logger.error(traceback.format_exc())

        if not user:
            logger.warning(
                "checkout.session.completed: no user found for customer=%s",
                customer_id,
            )
            return

        logger.info(
            "Upgrading user %s (%s) to Pro (subscription=%s)",
            user.id,
            user.email,
            subscription_id,
        )

        user.plan = "pro"
        sub = _get_or_create_subscription(user.id, db)
        sub.plan = "pro"
        sub.status = "active"
        sub.stripe_subscription_id = subscription_id
        sub.stripe_customer_id = customer_id

        current_period_end = None
        if current_period_end:
            try:
                sub.current_period_end = datetime.fromtimestamp(
                    int(current_period_end), tz=timezone.utc
                )
            except (TypeError, ValueError, OSError) as exc:
                logger.warning(
                    "Invalid current_period_end value %s: %s",
                    current_period_end,
                    exc,
                )

        usage = _get_or_create_usage_record(user.id, db)
        usage.conversions_limit = 100
        db.commit()
        logger.info("User %s upgraded to Pro successfully", user.id)


PLANS = [
    {
        "id": "free",
        "name": "Free",
        "price": 0,
        "features": [
            "5 conversions/month",
            "Basic templates",
        ],
    },
    {
        "id": "pro",
        "name": "Pro",
        "price": 9.99,
        "features": [
            "100 conversions/month",
            "All templates",
            "Priority support",
        ],
    },
]


@router.get(
    "/api/v2/billing/usage",
    summary="Get current user's usage and plan info",
)
def get_usage(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> dict:
    usage = _get_or_create_usage_record(user.id, db)
    limit = _get_or_create_subscription(user.id, db)
    usage_limit = 100 if limit.plan == "pro" else usage.conversions_limit
    return {
        "plan": limit.plan,
        "monthly_usage": usage.conversions_used,
        "limit": usage_limit,
    }


@router.get(
    "/api/v2/billing/plans",
    summary="List available subscription plans",
)
def list_plans() -> dict:
    return {"plans": PLANS}


@router.get(
    "/api/v2/billing/subscription",
    summary="Get current user's subscription status",
)
def get_subscription(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> dict:
    sub = _get_or_create_subscription(user.id, db)
    usage = _get_or_create_usage_record(user.id, db)
    return {
        "plan": sub.plan,
        "status": sub.status,
        "conversions_used": usage.conversions_used,
        "conversions_limit": usage.conversions_limit,
        "current_period_end": sub.current_period_end.isoformat() if sub.current_period_end else None,
    }


@router.post(
    "/api/v2/billing/checkout",
    summary="Create a Stripe Checkout Session for Pro upgrade",
)
async def create_checkout_session(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> dict:
    stripe.api_key = _stripe_secret()

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email)
        customer_id = customer.id
        db_user = db.get(User, user.id)
        if db_user:
            db_user.stripe_customer_id = customer_id
            db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card"],
        line_items=[
            {
                "price": _pro_price_id(),
                "quantity": 1,
            },
        ],
        mode="subscription",
        success_url=os.getenv(
            "STRIPE_SUCCESS_URL",
            "http://localhost:3000/billing?success=true",
        ),
        cancel_url=os.getenv(
            "STRIPE_CANCEL_URL",
            "http://localhost:3000/billing?canceled=true",
        ),
    )

    return {"checkout_url": session.url}


@router.post(
    "/api/v2/billing/webhook",
    summary="Handle Stripe webhook events",
)
async def stripe_webhook(request: Request) -> dict:
    stripe.api_key = _stripe_secret()

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET")

    if not sig_header or not webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header or webhook secret",
        )

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    event_type = event["type"]

    if event_type == "checkout.session.completed":
        try:
            _handle_checkout_completed(event)
        except Exception:
            logger.error("Unhandled error in checkout.session.completed handler")
            logger.error(traceback.format_exc())
            raise

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = _extract_stripe_id(subscription.customer)

        if customer_id:
            with SessionLocal() as db:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
                if user:
                    user.plan = "free"
                    sub = _get_or_create_subscription(user.id, db)
                    sub.plan = "free"
                    sub.status = "canceled"
                    usage = _get_or_create_usage_record(user.id, db)
                    usage.conversions_limit = 5
                    db.commit()

    elif event_type == "customer.subscription.updated":
        subscription = event["data"]["object"]
        customer_id = _extract_stripe_id(subscription.customer)
        status_str = subscription.status

        if customer_id:
            with SessionLocal() as db:
                user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
                if user:
                    sub = _get_or_create_subscription(user.id, db)
                    sub.status = status_str
                    if subscription.current_period_end:
                        sub.current_period_end = datetime.fromtimestamp(
                            subscription.current_period_end, tz=timezone.utc
                        )
                    db.commit()

    return {"received": True}


@router.post(
    "/api/v2/billing/portal",
    summary="Create a Stripe Customer Portal session",
)
async def create_portal_session(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> dict:
    stripe.api_key = _stripe_secret()

    customer_id = user.stripe_customer_id
    if not customer_id:
        customer = stripe.Customer.create(email=user.email)
        customer_id = customer.id
        db_user = db.get(User, user.id)
        if db_user:
            db_user.stripe_customer_id = customer_id
            db.commit()

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=os.getenv(
            "STRIPE_RETURN_URL",
            "http://localhost:3000/billing",
        ),
    )

    return {"portal_url": session.url}


__all__ = ["router"]
