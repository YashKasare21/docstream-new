"""
Stripe billing endpoints.

* ``POST /api/v2/billing/checkout`` — creates a Stripe Checkout Session
  for the Pro plan. Requires authentication.

* ``POST /api/v2/billing/webhook`` — receives Stripe webhook events.
  MUST have zero auth dependencies. Uses raw request body for signature
  verification.

* ``GET /api/v2/billing/usage`` — returns the authenticated user's plan,
  monthly usage count, and limit for the frontend billing page.
"""

from __future__ import annotations

import os

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from docstream_api.database import get_db
from docstream_api.db_models import User
from docstream_api.limits import FREE_TIER_LIMIT, get_or_create_user

router = APIRouter()

# ── Helpers ──────────────────────────────────────────────────────────────────


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


# ── Usage ────────────────────────────────────────────────────────────────────


@router.get(
    "/api/v2/billing/usage",
    summary="Get the authenticated user's plan, usage, and limit",
)
def get_usage(
    user: User = Depends(get_or_create_user),
) -> dict:
    """Return the user's current plan, monthly usage count, and limit.

    ``limit`` is ``5`` for free-tier users and ``-1`` (unlimited) for Pro users.
    """
    return {
        "plan": user.plan,
        "monthly_usage": user.monthly_usage,
        "limit": FREE_TIER_LIMIT if user.plan == "free" else -1,
    }


# ── Checkout ─────────────────────────────────────────────────────────────────


@router.post(
    "/api/v2/billing/checkout",
    summary="Create a Stripe Checkout Session for the Pro plan",
)
async def create_checkout_session(
    user: User = Depends(get_or_create_user),
    db: Session = Depends(get_db),
) -> dict:
    """Create a Stripe Checkout Session for the Pro plan.

    If the user doesn't have a ``stripe_customer_id`` yet, a Stripe
    Customer is created first.

    Returns the Checkout Session URL for the frontend to redirect to.
    """
    stripe.api_key = _stripe_secret()

    # Ensure the user has a Stripe Customer record.
    # Re-query the user from the injected DB session to avoid identity-map
    # issues (the ``user`` from ``get_or_create_user`` is attached to a
    # different session created by that dependency's own ``Depends(get_db)``).
    if not user.stripe_customer_id:
        customer = stripe.Customer.create(email=user.email)
        db_user = db.get(User, user.id)
        if db_user:
            db_user.stripe_customer_id = customer.id
            db.commit()

    session = stripe.checkout.Session.create(
        customer=user.stripe_customer_id,
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

    return {"url": session.url}


# ── Webhook ──────────────────────────────────────────────────────────────────


@router.post(
    "/api/v2/billing/webhook",
    summary="Stripe webhook handler",
)
async def stripe_webhook(request: Request) -> dict:
    """Handle Stripe webhook events.

    **CRITICAL**: This endpoint has NO auth dependencies. It reads the
    raw request body and verifies the Stripe signature.

    Handles:
    * ``checkout.session.completed`` — upgrades the user's plan to "pro".
    * ``customer.subscription.deleted`` — sets the user's plan back to "free".
    """
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
        session = event["data"]["object"]
        customer_id = session.get("customer")

        if customer_id:
            from docstream_api.database import SessionLocal

            with SessionLocal() as db:
                user = db.query(User).filter(
                    User.stripe_customer_id == customer_id
                ).first()
                if user:
                    user.plan = "pro"
                    db.commit()

    elif event_type == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        customer_id = subscription.get("customer")

        if customer_id:
            from docstream_api.database import SessionLocal

            with SessionLocal() as db:
                user = db.query(User).filter(
                    User.stripe_customer_id == customer_id
                ).first()
                if user:
                    user.plan = "free"
                    db.commit()

    return {"received": True}


__all__ = ["router"]
