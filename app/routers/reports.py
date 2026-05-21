from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import Charge, MRRReport, Plan, Refund, RevenueReport, Subscription

router = APIRouter(tags=["reports"])


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.get("/reports/revenue", response_model=RevenueReport)
def read_revenue_report(
    start: datetime | None = None,
    end: datetime | None = None,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    end = _aware(end) if end else datetime.now(timezone.utc)
    start = _aware(start) if start else end - timedelta(days=30)

    charges = session.exec(
        select(Charge).where(
            Charge.tenant_id == tenant, Charge.status == "succeeded"
        )
    ).all()
    in_range = [c for c in charges if start <= _aware(c.created) <= end]
    gross = sum(c.amount for c in in_range)

    refunds = session.exec(
        select(Refund).where(Refund.tenant_id == tenant)
    ).all()
    refunded = sum(
        r.amount for r in refunds if start <= _aware(r.created) <= end
    )

    return RevenueReport(
        start=start,
        end=end,
        currency="usd",
        gross=gross,
        refunded=refunded,
        net=gross - refunded,
        charge_count=len(in_range),
    )


@router.get("/reports/mrr", response_model=MRRReport)
def read_mrr(
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    subscriptions = session.exec(
        select(Subscription).where(
            Subscription.tenant_id == tenant, Subscription.status == "active"
        )
    ).all()
    plans = {
        p.id: p
        for p in session.exec(select(Plan).where(Plan.tenant_id == tenant)).all()
    }

    mrr = 0
    counted = 0
    for subscription in subscriptions:
        plan = plans.get(subscription.plan_id)
        if not plan:
            continue
        mrr += plan.amount // 12 if plan.interval == "year" else plan.amount
        counted += 1

    return MRRReport(currency="usd", mrr=mrr, active_subscription_count=counted)
