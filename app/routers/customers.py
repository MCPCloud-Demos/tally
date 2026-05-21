from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..auth import require_api_key
from ..database import get_session
from ..models import Customer, CustomerCreate, CustomerRead, CustomerUpdate

router = APIRouter(tags=["customers"])


@router.get("/customers", response_model=list[CustomerRead])
def read_customers(
    email: str | None = None,
    limit: int = 20,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    query = select(Customer).where(Customer.tenant_id == tenant)
    if email:
        query = query.where(Customer.email == email)
    return session.exec(query.order_by(Customer.created.desc()).limit(limit)).all()


@router.post("/customers", response_model=CustomerRead, status_code=201)
def create_customer(
    body: CustomerCreate,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    customer = Customer(tenant_id=tenant, **body.model_dump())
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer


@router.get("/customers/{customer_id}", response_model=CustomerRead)
def read_customer(
    customer_id: str,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    customer = session.get(Customer, customer_id)
    if not customer or customer.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.patch("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: str,
    body: CustomerUpdate,
    tenant: str = Depends(require_api_key),
    session: Session = Depends(get_session),
):
    customer = session.get(Customer, customer_id)
    if not customer or customer.tenant_id != tenant:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)
    session.add(customer)
    session.commit()
    session.refresh(customer)
    return customer
