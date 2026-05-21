def test_auth_required(client):
    assert client.get("/customers").status_code == 401
    assert client.get(
        "/customers", headers={"Authorization": "Bearer wrong"}
    ).status_code == 401


def test_openapi_is_terse(client):
    spec = client.get("/openapi.json").json()
    assert spec["openapi"].startswith("3.1")
    operations = [
        op for path in spec["paths"].values() for op in path.values()
    ]
    assert len(operations) == 21
    # The "before" state: auto-generated summaries, no descriptions.
    assert all(op.get("description") is None for op in operations)
    summaries = {op["summary"] for op in operations}
    assert "Confirm Payment Intent" in summaries


def test_seed_data_present(client, auth):
    customers = client.get("/customers?limit=50", headers=auth).json()
    assert len(customers) == 25
    plans = client.get("/plans", headers=auth).json()
    assert len(plans) == 6


def test_payment_intent_lifecycle(client, auth):
    customer = client.post(
        "/customers", headers=auth, json={"name": "Test", "email": "t@test.com"}
    ).json()
    pm = client.post(
        "/payment-methods",
        headers=auth,
        json={"card_number": "4242424242424242", "exp_month": 1, "exp_year": 2030, "cvc": "1"},
    ).json()
    client.post(
        f"/payment-methods/{pm['id']}/attach",
        headers=auth,
        json={"customer_id": customer["id"]},
    )
    intent = client.post(
        "/payment-intents",
        headers=auth,
        json={"amount": 4200, "customer_id": customer["id"], "payment_method_id": pm["id"]},
    ).json()
    confirmed = client.post(
        f"/payment-intents/{intent['id']}/confirm", headers=auth, json={}
    ).json()
    assert confirmed["status"] == "succeeded"


def test_large_intent_requires_action(client, auth):
    customer = client.post(
        "/customers", headers=auth, json={"name": "Big", "email": "b@test.com"}
    ).json()
    pm = client.post(
        "/payment-methods",
        headers=auth,
        json={"card_number": "5555555555554444", "exp_month": 1, "exp_year": 2030, "cvc": "1"},
    ).json()
    intent = client.post(
        "/payment-intents",
        headers=auth,
        json={"amount": 90000, "customer_id": customer["id"], "payment_method_id": pm["id"]},
    ).json()
    confirmed = client.post(
        f"/payment-intents/{intent['id']}/confirm", headers=auth, json={}
    ).json()
    assert confirmed["status"] == "requires_action"


def test_refund_caps_at_charge_amount(client, auth):
    charge = client.get("/charges?limit=1", headers=auth).json()[0]
    over = client.post(
        "/refunds",
        headers=auth,
        json={"charge_id": charge["id"], "amount": charge["amount"] * 5},
    )
    assert over.status_code == 400


def test_reports(client, auth):
    mrr = client.get("/reports/mrr", headers=auth).json()
    assert mrr["mrr"] > 0 and mrr["active_subscription_count"] > 0
    revenue = client.get("/reports/revenue", headers=auth).json()
    assert revenue["net"] == revenue["gross"] - revenue["refunded"]


def test_not_found(client, auth):
    assert client.get("/customers/cus_missing", headers=auth).status_code == 404
