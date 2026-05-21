"""In-app traffic generator.

A background task that periodically calls a rotating handful of Tally
endpoints, so the deployed demo always shows live activity — warm machines,
non-empty access logs, a steady stream of DB queries. Enabled on the Fly
deployment via ENABLE_TRAFFIC_GENERATOR; off by default so local dev and the
test suite never start a background loop.
"""

import asyncio
import logging
import random

import httpx

from .config import get_settings

logger = logging.getLogger("tally.traffic")

# Read endpoints — safe, idempotent, no data growth.
_READ_PATHS = [
    "/customers?limit=5",
    "/plans",
    "/payment-intents?limit=5",
    "/payment-intents?status=requires_payment_method",
    "/charges?limit=5",
    "/invoices?status=open",
    "/subscriptions?status=active",
    "/reports/mrr",
    "/reports/revenue",
]


async def _read_cycle(client: httpx.AsyncClient, headers: dict) -> None:
    # A random handful each cycle, so traffic looks organic and, over time,
    # every read endpoint gets exercised.
    for path in random.sample(_READ_PATHS, k=5):
        try:
            await client.get(path, headers=headers)
        except Exception as exc:  # a traffic error must never escape
            logger.warning("traffic read %s failed: %s", path, exc)


async def _write_cycle(client: httpx.AsyncClient, headers: dict) -> None:
    # Exercise the write path: open a payment intent on a random customer
    # and cancel it. Anything created here is cleared by the nightly reset.
    try:
        resp = await client.get("/customers?limit=20", headers=headers)
        customers = resp.json()
        if not isinstance(customers, list) or not customers:
            return
        customer = random.choice(customers)
        created = await client.post(
            "/payment-intents",
            headers=headers,
            json={
                "amount": random.choice([1200, 3400, 8900]),
                "customer_id": customer["id"],
            },
        )
        intent = created.json()
        if isinstance(intent, dict) and intent.get("id"):
            await client.post(
                f"/payment-intents/{intent['id']}/cancel", headers=headers
            )
    except Exception as exc:
        logger.warning("traffic write cycle failed: %s", exc)


async def run_traffic_generator() -> None:
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.demo_api_key}"}
    interval = settings.traffic_interval_seconds
    logger.info(
        "traffic generator enabled — every %ss against %s",
        interval,
        settings.traffic_target_url,
    )
    cycle = 0
    async with httpx.AsyncClient(
        base_url=settings.traffic_target_url, timeout=10.0
    ) as client:
        while True:
            try:
                await asyncio.sleep(interval)
                cycle += 1
                await _read_cycle(client, headers)
                # Every fifth cycle also exercises a create + cancel.
                if cycle % 5 == 0:
                    await _write_cycle(client, headers)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("traffic cycle error: %s", exc)
