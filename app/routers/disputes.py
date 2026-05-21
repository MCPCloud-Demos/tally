from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import Dispute, DisputeRead, RespondToDispute

router = APIRouter(tags=["disputes"])


@router.get("/disputes", response_model=list[DisputeRead])
def read_disputes(
    status: str | None = None,
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(Dispute).where(Dispute.tenant_id == tenant)
    if status:
        query = query.where(Dispute.status == status)
    return session.exec(query.order_by(Dispute.created.desc()).limit(limit)).all()


@router.post("/disputes/{dispute_id}/respond", response_model=DisputeRead)
def respond_to_dispute(
    dispute_id: str,
    body: RespondToDispute,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    dispute = session.get(Dispute, dispute_id)
    if not dispute or dispute.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Dispute not found")
    if dispute.status != "needs_response":
        raise HTTPException(status_code=409, detail=f"Dispute is {dispute.status}")
    dispute.evidence = body.evidence
    dispute.status = "under_review"
    session.add(dispute)
    session.commit()
    session.refresh(dispute)
    return dispute
