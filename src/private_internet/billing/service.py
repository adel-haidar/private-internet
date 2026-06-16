"""Subscription entitlement + Stripe webhook event handling."""

import logging
from datetime import datetime, timezone

from fastapi import Depends, HTTPException

from private_internet.billing import stripe_client
from private_internet.billing.plans import (
    ENTITLED_STATUSES,
    FEATURE_MIN_PLAN,
    effective_plan,
    has_feature,
    price_to_plan,
)
from private_internet.config import get_settings
from private_internet.core.request_context import RequestContext, get_request_context
from private_internet.users.service import (
    get_user_by_id,
    get_user_by_stripe_customer_id,
    set_stripe_customer_id,
    set_subscription,
)

logger = logging.getLogger(__name__)


def is_entitled(user: dict) -> bool:
    """Whether a user may use the platform at all (any tier, incl. free).

    With three tiers, "free" is itself a valid in-app tier, so every resolved
    plan is entitled. Kept for back-compat with the old single-tier gate.
    """
    settings = get_settings()
    if not settings.billing_enabled:
        return True
    if user.get("is_admin"):
        return True
    # Free is a real tier now — anyone who resolves to a plan may use the app.
    return True


def require_feature(feature: str):
    """FastAPI dependency factory: 402 if the caller's plan lacks ``feature``.

    Uses 402 (Payment Required) deliberately — NOT 403/404, which CloudFront
    rewrites into the SPA index.html and would break the dashboard's JSON
    parsing (see agents/assistant/shared/auth.py).
    """

    async def _dep(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        user = get_user_by_id(ctx.user_id) or {}
        if not has_feature(user, feature):
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "upgrade_required",
                    "feature": feature,
                    "required_plan": FEATURE_MIN_PLAN[feature],
                    "current_plan": effective_plan(user),
                },
            )
        return ctx

    return _dep


def ensure_customer(user: dict) -> str:
    """Return the user's Stripe customer id, creating + persisting one if needed."""
    existing = user.get("stripe_customer_id")
    if existing:
        return existing
    customer_id = stripe_client.create_customer(user["email"], str(user["id"]))
    set_stripe_customer_id(str(user["id"]), customer_id)
    return customer_id


def _ts_to_dt(ts) -> datetime | None:
    try:
        return datetime.fromtimestamp(int(ts), tz=timezone.utc)
    except (TypeError, ValueError):
        return None


def _subscription_price_id(sub_obj: dict) -> str | None:
    """First line item's price id from a Stripe subscription object."""
    items = ((sub_obj.get("items") or {}).get("data")) or []
    if not items:
        return None
    return ((items[0].get("price") or {}).get("id")) or None


def handle_event(event: dict) -> None:
    """Apply a verified Stripe webhook event to the user's subscription state."""
    etype = event.get("type", "")
    obj = (event.get("data") or {}).get("object") or {}

    if etype == "checkout.session.completed":
        user_id = obj.get("client_reference_id")
        customer = obj.get("customer")
        subscription = obj.get("subscription")
        if user_id:
            if customer:
                set_stripe_customer_id(str(user_id), customer)
            # The authoritative status arrives via subscription.* shortly after;
            # mark active now so the user isn't bounced on the success redirect.
            set_subscription(str(user_id), status="active", stripe_subscription_id=subscription)
            logger.info(f"[user:{str(user_id)[:8]}] checkout completed")

    elif etype in ("customer.subscription.created", "customer.subscription.updated"):
        customer = obj.get("customer")
        user = get_user_by_stripe_customer_id(customer) if customer else None
        if user:
            status = obj.get("status", "active")
            # Derive the tier from the subscription's price. Plan-change/upgrade
            # via the Billing Portal arrives here too and re-maps automatically.
            plan = price_to_plan(_subscription_price_id(obj))
            # An active sub with an unrecognised price still grants pro (safe
            # default); a non-active sub drops the user back to free.
            if status not in ENTITLED_STATUSES:
                plan = "free"
            elif plan is None:
                plan = "pro"
            set_subscription(
                str(user["id"]),
                status=status,
                stripe_subscription_id=obj.get("id"),
                current_period_end=_ts_to_dt(obj.get("current_period_end")),
                plan=plan,
            )
            logger.info(f"[user:{str(user['id'])[:8]}] subscription -> {status} (plan={plan})")

    elif etype == "customer.subscription.deleted":
        customer = obj.get("customer")
        user = get_user_by_stripe_customer_id(customer) if customer else None
        if user:
            set_subscription(
                str(user["id"]),
                status="canceled",
                stripe_subscription_id=obj.get("id"),
                plan="free",
            )
            logger.info(f"[user:{str(user['id'])[:8]}] subscription canceled")

    else:
        logger.debug(f"Ignoring Stripe event: {etype}")
