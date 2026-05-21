from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import Charge, Invoice, InvoiceRead

router = APIRouter(tags=["invoices"])


@router.get("/invoices", response_model=list[InvoiceRead])
def read_invoices(
    customer_id: str | None = None,
    status: str | None = None,
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(Invoice).where(Invoice.tenant_id == tenant)
    if customer_id:
        query = query.where(Invoice.customer_id == customer_id)
    if status:
        query = query.where(Invoice.status == status)
    return session.exec(query.order_by(Invoice.created.desc()).limit(limit)).all()


@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceRead)
def pay_invoice(
    invoice_id: str,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    invoice = session.get(Invoice, invoice_id)
    if not invoice or invoice.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "paid":
        raise HTTPException(status_code=409, detail="Invoice already paid")
    if invoice.status not in ("open", "draft"):
        raise HTTPException(status_code=409, detail=f"Invoice is {invoice.status}")

    invoice.status = "paid"
    invoice.amount_paid = invoice.amount_due
    session.add(invoice)
    session.add(
        Charge(
            tenant_id=tenant,
            amount=invoice.amount_due,
            currency=invoice.currency,
            customer_id=invoice.customer_id,
        )
    )
    session.commit()
    session.refresh(invoice)
    return invoice
