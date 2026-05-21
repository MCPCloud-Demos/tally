from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import Charge, ChargeRead

router = APIRouter(tags=["charges"])


@router.get("/charges", response_model=list[ChargeRead])
def read_charges(
    customer_id: str | None = None,
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(Charge).where(Charge.tenant_id == tenant)
    if customer_id:
        query = query.where(Charge.customer_id == customer_id)
    return session.exec(query.order_by(Charge.created.desc()).limit(limit)).all()
