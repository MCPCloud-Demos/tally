from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from ..auth import require_api_key
from ..database import get_session
from ..models import (
    AttachPaymentMethod,
    Customer,
    PaymentMethod,
    PaymentMethodCreate,
    PaymentMethodRead,
)

router = APIRouter(tags=["payment_methods"])

_BRANDS = {"4": "visa", "5": "mastercard", "3": "amex", "6": "discover"}


@router.post("/payment-methods", response_model=PaymentMethodRead, status_code=201)
def create_payment_method(
    body: PaymentMethodCreate,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    digits = body.card_number.replace(" ", "")
    payment_method = PaymentMethod(
        tenant_id=tenant,
        type=body.type,
        brand=_BRANDS.get(digits[:1], "unknown"),
        last4=digits[-4:],
        exp_month=body.exp_month,
        exp_year=body.exp_year,
    )
    session.add(payment_method)
    session.commit()
    session.refresh(payment_method)
    return payment_method


@router.post(
    "/payment-methods/{payment_method_id}/attach", response_model=PaymentMethodRead
)
def attach_payment_method(
    payment_method_id: str,
    body: AttachPaymentMethod,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    payment_method = session.get(PaymentMethod, payment_method_id)
    if not payment_method or payment_method.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Payment method not found")
    customer = session.get(Customer, body.customer_id)
    if not customer or customer.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Customer not found")
    payment_method.customer_id = body.customer_id
    session.add(payment_method)
    session.commit()
    session.refresh(payment_method)
    return payment_method
