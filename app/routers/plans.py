from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import Plan, PlanRead

router = APIRouter(tags=["plans"])


@router.get("/plans", response_model=list[PlanRead])
def read_plans(
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(Plan).where(Plan.tenant_id == tenant)
    return session.exec(query.order_by(Plan.amount).limit(limit)).all()
