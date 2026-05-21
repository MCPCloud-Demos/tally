from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import (
    Customer,
    Plan,
    Subscription,
    SubscriptionCreate,
    SubscriptionRead,
)

router = APIRouter(tags=["subscriptions"])


@router.post("/subscriptions", response_model=SubscriptionRead, status_code=201)
def create_subscription(
    body: SubscriptionCreate,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    customer = session.get(Customer, body.customer_id)
    if not customer or customer.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Customer not found")
    plan = session.get(Plan, body.plan_id)
    if not plan or plan.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Plan not found")

    now = datetime.now(timezone.utc)
    days = 365 if plan.interval == "year" else 30
    subscription = Subscription(
        tenant_id=tenant,
        customer_id=body.customer_id,
        plan_id=body.plan_id,
        status="trialing" if body.trial else "active",
        current_period_start=now,
        current_period_end=now + timedelta(days=days),
    )
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return subscription


@router.get("/subscriptions", response_model=list[SubscriptionRead])
def read_subscriptions(
    customer_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(Subscription).where(Subscription.tenant_id == tenant)
    if customer_id:
        query = query.where(Subscription.customer_id == customer_id)
    if status:
        query = query.where(Subscription.status == status)
    return session.exec(
        query.order_by(Subscription.created.desc()).limit(limit)
    ).all()


@router.post(
    "/subscriptions/{subscription_id}/cancel", response_model=SubscriptionRead
)
def cancel_subscription(
    subscription_id: str,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    subscription = session.get(Subscription, subscription_id)
    if not subscription or subscription.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Subscription not found")
    subscription.status = "canceled"
    subscription.cancel_at_period_end = False
    session.add(subscription)
    session.commit()
    session.refresh(subscription)
    return subscription
