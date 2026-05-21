from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import get_settings
from .database import init_db
from .routers import (
    charges,
    customers,
    disputes,
    invoices,
    payment_intents,
    payment_methods,
    plans,
    refunds,
    reports,
    subscriptions,
)
from .seed import seed_if_empty


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if get_settings().seed_on_startup:
        seed_if_empty()
    yield


app = FastAPI(title="Tally — Payments & Billing API", version="1.0.0", lifespan=lifespan)

app.include_router(customers.router)
app.include_router(payment_methods.router)
app.include_router(payment_intents.router)
app.include_router(refunds.router)
app.include_router(charges.router)
app.include_router(plans.router)
app.include_router(subscriptions.router)
app.include_router(invoices.router)
app.include_router(reports.router)

# v1.1 drift-detection addition — off by default, flip ENABLE_DISPUTES to expose.
if get_settings().enable_disputes:
    app.include_router(disputes.router)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}
