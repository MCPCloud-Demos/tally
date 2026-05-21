import secrets
from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _id(prefix: str):
    return lambda: f"{prefix}_{secrets.token_hex(12)}"


# --- Customer -------------------------------------------------------------


class CustomerBase(SQLModel):
    name: str
    email: str
    description: str | None = None


class Customer(CustomerBase, table=True):
    __tablename__ = "customers"
    id: str = Field(default_factory=_id("cus"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)


class CustomerCreate(CustomerBase):
    pass


class CustomerUpdate(SQLModel):
    name: str | None = None
    email: str | None = None
    description: str | None = None


class CustomerRead(CustomerBase):
    id: str
    created: datetime


# --- Payment method -------------------------------------------------------


class PaymentMethod(SQLModel, table=True):
    __tablename__ = "payment_methods"
    id: str = Field(default_factory=_id("pm"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    type: str = "card"
    customer_id: str | None = None
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class PaymentMethodCreate(SQLModel):
    type: str = "card"
    card_number: str
    exp_month: int
    exp_year: int
    cvc: str


class PaymentMethodRead(SQLModel):
    id: str
    created: datetime
    type: str
    customer_id: str | None = None
    brand: str
    last4: str
    exp_month: int
    exp_year: int


class AttachPaymentMethod(SQLModel):
    customer_id: str


# --- Payment intent -------------------------------------------------------


class PaymentIntentBase(SQLModel):
    amount: int
    currency: str = "usd"
    customer_id: str
    payment_method_id: str | None = None
    description: str | None = None


class PaymentIntent(PaymentIntentBase, table=True):
    __tablename__ = "payment_intents"
    id: str = Field(default_factory=_id("pi"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    status: str = "requires_payment_method"


class PaymentIntentCreate(PaymentIntentBase):
    pass


class PaymentIntentRead(PaymentIntentBase):
    id: str
    created: datetime
    status: str


class ConfirmPaymentIntent(SQLModel):
    payment_method_id: str | None = None


# --- Charge ---------------------------------------------------------------


class Charge(SQLModel, table=True):
    __tablename__ = "charges"
    id: str = Field(default_factory=_id("ch"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    amount: int
    currency: str = "usd"
    customer_id: str
    payment_intent_id: str | None = None
    payment_method_id: str | None = None
    status: str = "succeeded"
    paid: bool = True
    refunded: bool = False
    amount_refunded: int = 0


class ChargeRead(SQLModel):
    id: str
    created: datetime
    amount: int
    currency: str
    customer_id: str
    payment_intent_id: str | None = None
    payment_method_id: str | None = None
    status: str
    paid: bool
    refunded: bool
    amount_refunded: int


# --- Refund ---------------------------------------------------------------


class Refund(SQLModel, table=True):
    __tablename__ = "refunds"
    id: str = Field(default_factory=_id("re"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    charge_id: str
    amount: int
    currency: str = "usd"
    status: str = "succeeded"
    reason: str | None = None


class RefundCreate(SQLModel):
    charge_id: str
    amount: int | None = None
    reason: str | None = None


class RefundRead(SQLModel):
    id: str
    created: datetime
    charge_id: str
    amount: int
    currency: str
    status: str
    reason: str | None = None


# --- Plan -----------------------------------------------------------------


class Plan(SQLModel, table=True):
    __tablename__ = "plans"
    id: str = Field(default_factory=_id("plan"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    nickname: str
    amount: int
    currency: str = "usd"
    interval: str
    product: str


class PlanRead(SQLModel):
    id: str
    created: datetime
    nickname: str
    amount: int
    currency: str
    interval: str
    product: str


# --- Subscription ---------------------------------------------------------


class Subscription(SQLModel, table=True):
    __tablename__ = "subscriptions"
    id: str = Field(default_factory=_id("sub"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    customer_id: str
    plan_id: str
    status: str = "active"
    current_period_start: datetime = Field(default_factory=_now)
    current_period_end: datetime = Field(default_factory=_now)
    cancel_at_period_end: bool = False


class SubscriptionCreate(SQLModel):
    customer_id: str
    plan_id: str
    trial: bool = False


class SubscriptionRead(SQLModel):
    id: str
    created: datetime
    customer_id: str
    plan_id: str
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool


# --- Invoice --------------------------------------------------------------


class Invoice(SQLModel, table=True):
    __tablename__ = "invoices"
    id: str = Field(default_factory=_id("in"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    customer_id: str
    subscription_id: str | None = None
    amount_due: int
    amount_paid: int = 0
    currency: str = "usd"
    status: str = "draft"
    due_date: datetime | None = None


class InvoiceRead(SQLModel):
    id: str
    created: datetime
    customer_id: str
    subscription_id: str | None = None
    amount_due: int
    amount_paid: int
    currency: str
    status: str
    due_date: datetime | None = None


# --- Dispute (v1.1 drift-detection addition) ------------------------------


class Dispute(SQLModel, table=True):
    __tablename__ = "disputes"
    id: str = Field(default_factory=_id("dp"), primary_key=True)
    tenant_id: str = Field(index=True)
    created: datetime = Field(default_factory=_now)
    charge_id: str
    amount: int
    currency: str = "usd"
    status: str = "needs_response"
    reason: str
    evidence: str | None = None


class DisputeRead(SQLModel):
    id: str
    created: datetime
    charge_id: str
    amount: int
    currency: str
    status: str
    reason: str
    evidence: str | None = None


class RespondToDispute(SQLModel):
    evidence: str


# --- Reports --------------------------------------------------------------


class RevenueReport(SQLModel):
    start: datetime
    end: datetime
    currency: str
    gross: int
    refunded: int
    net: int
    charge_count: int


class MRRReport(SQLModel):
    currency: str
    mrr: int
    active_subscription_count: int
