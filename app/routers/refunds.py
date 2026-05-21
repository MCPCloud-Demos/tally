from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import require_api_key
from ..database import get_session
from ..models import Charge, Refund, RefundCreate, RefundRead

router = APIRouter(tags=["refunds"])


@router.post("/refunds", response_model=RefundRead, status_code=201)
def create_refund(
    body: RefundCreate,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    charge = session.get(Charge, body.charge_id)
    if not charge or charge.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Charge not found")
    if charge.status != "succeeded":
        raise HTTPException(status_code=409, detail="Charge is not refundable")
    refundable = charge.amount - charge.amount_refunded
    amount = body.amount if body.amount is not None else refundable
    if amount <= 0 or amount > refundable:
        raise HTTPException(status_code=400, detail="Invalid refund amount")

    refund = Refund(
        tenant_id=tenant,
        charge_id=charge.id,
        amount=amount,
        currency=charge.currency,
        reason=body.reason,
    )
    charge.amount_refunded += amount
    charge.refunded = charge.amount_refunded >= charge.amount
    session.add(refund)
    session.add(charge)
    session.commit()
    session.refresh(refund)
    return refund
