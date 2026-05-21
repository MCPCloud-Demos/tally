from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import (
    Charge,
    ConfirmPaymentIntent,
    PaymentIntent,
    PaymentIntentCreate,
    PaymentIntentRead,
    PaymentMethod,
)

router = APIRouter(tags=["payment_intents"])

# Above this amount confirmation returns requires_action instead of succeeding.
_ACTION_THRESHOLD = 50000


@router.get("/payment-intents", response_model=list[PaymentIntentRead])
def read_payment_intents(
    customer_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(PaymentIntent).where(PaymentIntent.tenant_id == tenant)
    if customer_id:
        query = query.where(PaymentIntent.customer_id == customer_id)
    if status:
        query = query.where(PaymentIntent.status == status)
    return session.exec(
        query.order_by(PaymentIntent.created.desc()).limit(limit)
    ).all()


@router.post("/payment-intents", response_model=PaymentIntentRead, status_code=201)
def create_payment_intent(
    body: PaymentIntentCreate,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    intent = PaymentIntent(tenant_id=tenant, **body.model_dump())
    if intent.payment_method_id:
        intent.status = "requires_confirmation"
    session.add(intent)
    session.commit()
    session.refresh(intent)
    return intent


@router.get("/payment-intents/{payment_intent_id}", response_model=PaymentIntentRead)
def read_payment_intent(
    payment_intent_id: str,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    intent = session.get(PaymentIntent, payment_intent_id)
    if not intent or intent.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    return intent


@router.post(
    "/payment-intents/{payment_intent_id}/confirm", response_model=PaymentIntentRead
)
def confirm_payment_intent(
    payment_intent_id: str,
    body: ConfirmPaymentIntent | None = None,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    intent = session.get(PaymentIntent, payment_intent_id)
    if not intent or intent.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    if intent.status in ("succeeded", "canceled"):
        raise HTTPException(
            status_code=409, detail=f"Payment intent is {intent.status}"
        )
    if body and body.payment_method_id:
        intent.payment_method_id = body.payment_method_id
    if not intent.payment_method_id:
        raise HTTPException(status_code=409, detail="No payment method attached")
    pm = session.get(PaymentMethod, intent.payment_method_id)
    if not pm or pm.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Payment method not found")

    if intent.amount >= _ACTION_THRESHOLD:
        intent.status = "requires_action"
    else:
        intent.status = "succeeded"
        session.add(
            Charge(
                tenant_id=tenant,
                amount=intent.amount,
                currency=intent.currency,
                customer_id=intent.customer_id,
                payment_intent_id=intent.id,
                payment_method_id=intent.payment_method_id,
            )
        )
    session.add(intent)
    session.commit()
    session.refresh(intent)
    return intent


@router.post(
    "/payment-intents/{payment_intent_id}/cancel", response_model=PaymentIntentRead
)
def cancel_payment_intent(
    payment_intent_id: str,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    intent = session.get(PaymentIntent, payment_intent_id)
    if not intent or intent.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Payment intent not found")
    if intent.status == "succeeded":
        raise HTTPException(status_code=409, detail="Payment intent already succeeded")
    intent.status = "canceled"
    session.add(intent)
    session.commit()
    session.refresh(intent)
    return intent
