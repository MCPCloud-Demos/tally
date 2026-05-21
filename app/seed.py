"""Deterministic demo data for the Tally showcase tenant.

Run `python -m app.seed` to wipe and re-seed (used by the nightly reset job).
The app also seeds automatically on startup when the database is empty.
"""

import random
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from .database import engine, init_db
from .models import (
    Charge,
    Customer,
    Dispute,
    Invoice,
    PaymentIntent,
    PaymentMethod,
    Plan,
    Refund,
    Subscription,
)

TENANT = "demo"

_FIRST = [
    "Ava", "Liam", "Noah", "Mia", "Ethan", "Zoe", "Lucas", "Aria", "Mason",
    "Ivy", "Leo", "Nora", "Owen", "Ruby", "Eli", "Lena", "Kai", "Maya",
    "Jude", "Cora", "Finn", "Tess", "Rhys", "Wren", "Otto",
]
_LAST = [
    "Carter", "Nguyen", "Patel", "Okafor", "Reyes", "Haddad", "Larsen",
    "Cohen", "Mwangi", "Silva", "Novak", "Khan", "Park", "Rossi", "Adeyemi",
    "Berg", "Costa", "Dahl", "Engel", "Flores", "Gupta", "Hahn", "Ito",
    "Jakobsen", "Kowalski",
]

_PLANS = [
    ("Starter Monthly", 900, "month", "Tally Starter"),
    ("Starter Annual", 9000, "year", "Tally Starter"),
    ("Pro Monthly", 2900, "month", "Tally Pro"),
    ("Pro Annual", 29000, "year", "Tally Pro"),
    ("Business Monthly", 9900, "month", "Tally Business"),
    ("Scale Monthly", 24900, "month", "Tally Scale"),
]

_CARD_BRANDS = ["visa", "mastercard", "amex", "discover"]
_DISPUTE_REASONS = ["fraudulent", "product_not_received", "duplicate"]


def seed_if_empty(target_engine=engine) -> None:
    with Session(target_engine) as session:
        if session.exec(select(Customer).limit(1)).first():
            return
        _seed(session)


def reseed(target_engine=engine) -> None:
    init_db()
    with Session(target_engine) as session:
        for model in (
            Refund, Charge, Dispute, Invoice, Subscription,
            PaymentIntent, PaymentMethod, Plan, Customer,
        ):
            for row in session.exec(select(model)).all():
                session.delete(row)
        session.commit()
        _seed(session)


def _seed(session: Session) -> None:
    rng = random.Random(42)
    now = datetime.now(timezone.utc)

    def ago(days: int) -> datetime:
        return now - timedelta(days=days)

    # Plans -----------------------------------------------------------------
    plans: list[Plan] = []
    for nickname, amount, interval, product in _PLANS:
        plan = Plan(
            tenant_id=TENANT,
            nickname=nickname,
            amount=amount,
            interval=interval,
            product=product,
            created=ago(120),
        )
        session.add(plan)
        plans.append(plan)

    # Customers -------------------------------------------------------------
    customers: list[Customer] = []
    for i in range(25):
        first = _FIRST[i]
        last = _LAST[i]
        customer = Customer(
            tenant_id=TENANT,
            name=f"{first} {last}",
            email=f"{first}.{last}@example.com".lower(),
            description=rng.choice([None, "Imported from legacy billing", None]),
            created=ago(rng.randint(20, 110)),
        )
        session.add(customer)
        customers.append(customer)
    session.commit()

    # Payment methods (attached to the first 18 customers) ------------------
    payment_methods: dict[str, PaymentMethod] = {}
    for customer in customers[:18]:
        pm = PaymentMethod(
            tenant_id=TENANT,
            customer_id=customer.id,
            brand=rng.choice(_CARD_BRANDS),
            last4=f"{rng.randint(0, 9999):04d}",
            exp_month=rng.randint(1, 12),
            exp_year=rng.choice([2026, 2027, 2028]),
            created=customer.created,
        )
        session.add(pm)
        payment_methods[customer.id] = pm
    session.commit()

    # Subscriptions ---------------------------------------------------------
    statuses = (
        ["active"] * 8 + ["past_due"] * 3 + ["trialing"] * 2 + ["canceled"] * 2
    )
    rng.shuffle(statuses)
    subscriptions: list[Subscription] = []
    for i, status in enumerate(statuses):
        customer = customers[i]
        plan = rng.choice(plans)
        start = ago(rng.randint(8, 40))
        days = 365 if plan.interval == "year" else 30
        subscription = Subscription(
            tenant_id=TENANT,
            customer_id=customer.id,
            plan_id=plan.id,
            status=status,
            current_period_start=start,
            current_period_end=start + timedelta(days=days),
            cancel_at_period_end=(status == "active" and rng.random() < 0.2),
            created=start,
        )
        session.add(subscription)
        subscriptions.append(subscription)
    session.commit()

    plans_by_id = {p.id: p for p in plans}

    # Invoices --------------------------------------------------------------
    for subscription in subscriptions:
        plan = plans_by_id[subscription.plan_id]
        if subscription.status == "active":
            invoice_status, paid = "paid", plan.amount
        elif subscription.status == "past_due":
            invoice_status, paid = "open", 0
        elif subscription.status == "trialing":
            invoice_status, paid = "draft", 0
        else:
            invoice_status, paid = "uncollectible", 0
        issued = subscription.current_period_start
        session.add(
            Invoice(
                tenant_id=TENANT,
                customer_id=subscription.customer_id,
                subscription_id=subscription.id,
                amount_due=plan.amount,
                amount_paid=paid,
                currency="usd",
                status=invoice_status,
                due_date=issued + timedelta(days=7),
                created=issued,
            )
        )
    # A few extra unpaid one-off invoices for the recovery skill to find.
    for customer in rng.sample(customers, 4):
        amount = rng.choice([1500, 4900, 12000])
        session.add(
            Invoice(
                tenant_id=TENANT,
                customer_id=customer.id,
                amount_due=amount,
                currency="usd",
                status="open",
                due_date=ago(rng.randint(1, 9)),
                created=ago(rng.randint(10, 20)),
            )
        )
    session.commit()

    # Payment intents + charges --------------------------------------------
    intent_plan = (
        ["requires_payment_method"] * 4
        + ["succeeded"] * 4
        + ["requires_action"] * 2
        + ["canceled"] * 2
    )
    succeeded_charges: list[Charge] = []
    for i, status in enumerate(intent_plan):
        customer = customers[i + 4]
        pm = payment_methods.get(customer.id)
        amount = rng.choice([1900, 2900, 4500, 9900, 14900, 62000])
        created = ago(rng.randint(1, 26))
        intent = PaymentIntent(
            tenant_id=TENANT,
            amount=amount,
            currency="usd",
            customer_id=customer.id,
            payment_method_id=pm.id if pm and status != "requires_payment_method" else None,
            status=status,
            created=created,
        )
        session.add(intent)
        session.flush()
        if status == "succeeded":
            charge = Charge(
                tenant_id=TENANT,
                amount=amount,
                currency="usd",
                customer_id=customer.id,
                payment_intent_id=intent.id,
                payment_method_id=pm.id if pm else None,
                created=created,
            )
            session.add(charge)
            succeeded_charges.append(charge)

    # Charges for paid subscription invoices (drives the revenue report).
    for subscription in subscriptions:
        if subscription.status != "active":
            continue
        plan = plans_by_id[subscription.plan_id]
        created = subscription.current_period_start + timedelta(days=1)
        charge = Charge(
            tenant_id=TENANT,
            amount=plan.amount,
            currency="usd",
            customer_id=subscription.customer_id,
            created=created,
        )
        session.add(charge)
        succeeded_charges.append(charge)
    session.commit()

    # Refunds (partial history) --------------------------------------------
    for charge in rng.sample(succeeded_charges, 2):
        refund_amount = charge.amount // 2
        session.add(
            Refund(
                tenant_id=TENANT,
                charge_id=charge.id,
                amount=refund_amount,
                currency="usd",
                reason="requested_by_customer",
                created=charge.created + timedelta(days=2),
            )
        )
        charge.amount_refunded = refund_amount
        charge.refunded = False
        session.add(charge)

    # Disputes (v1.1 — surfaced only when ENABLE_DISPUTES is set) ----------
    for charge in rng.sample(succeeded_charges, 3):
        session.add(
            Dispute(
                tenant_id=TENANT,
                charge_id=charge.id,
                amount=charge.amount,
                currency="usd",
                status="needs_response",
                reason=rng.choice(_DISPUTE_REASONS),
                created=charge.created + timedelta(days=3),
            )
        )
    session.commit()


if __name__ == "__main__":
    reseed()
    print("Tally demo tenant re-seeded.")
