import asyncio
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
from .traffic import run_traffic_generator


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    if settings.seed_on_startup:
        seed_if_empty()
    traffic_task: asyncio.Task | None = None
    if settings.enable_traffic_generator:
        traffic_task = asyncio.create_task(run_traffic_generator())
    yield
    if traffic_task:
        traffic_task.cancel()
        try:
            await traffic_task
        except asyncio.CancelledError:
            pass


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
