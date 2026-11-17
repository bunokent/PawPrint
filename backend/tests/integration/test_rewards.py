"""Integration: rewards (Stripe test + GCash via PayMongo) and webhooks."""

import base64
import hashlib
import hmac
import json
import uuid

import httpx
import pytest

from apps.flyers.factories import FlyerFactory
from apps.rewards.models import RewardTransaction
from apps.webhooks.models import WebhookEvent

pytestmark = pytest.mark.django_db


class _FakeStripeSession:
    id = "cs_test_123"
    url = "https://checkout.stripe.com/pay/cs_test_123"


def _mock_stripe(monkeypatch):
    monkeypatch.setattr(
        "stripe.checkout.Session.create", lambda **kwargs: _FakeStripeSession()
    )


def test_create_stripe_reward(auth_client, user, monkeypatch):
    _mock_stripe(monkeypatch)
    flyer = FlyerFactory(creator=user, reward_enabled=True, reward_amount_cents=500000, reward_currency="PHP")
    resp = auth_client.post(
        "/api/rewards", {"flyer_id": str(flyer.pk), "provider": "stripe"}, format="json"
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["provider"] == "stripe"
    assert body["status"] == "pending"
    assert body["amount_cents"] == 500000
    assert body["checkout_url"] == "https://checkout.stripe.com/pay/cs_test_123"
    tx = RewardTransaction.objects.get(pk=body["transaction_id"])
    assert tx.provider_reference == "cs_test_123"


def test_create_reward_unknown_flyer_400(auth_client):
    resp = auth_client.post(
        "/api/rewards", {"flyer_id": str(uuid.uuid4()), "provider": "stripe"}, format="json"
    )
    assert resp.status_code == 400


def test_create_reward_requires_positive_amount(auth_client, user):
    flyer = FlyerFactory(creator=user, reward_enabled=False, reward_amount_cents=0)
    resp = auth_client.post(
        "/api/rewards", {"flyer_id": str(flyer.pk), "provider": "stripe", "amount_cents": 0}, format="json"
    )
    assert resp.status_code == 400


def test_create_gcash_reward_with_mock_transport(auth_client, user, monkeypatch, settings):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/checkout_sessions"
        auth = request.headers["Authorization"]
        assert auth.startswith("Basic ")
        payload = json.loads(request.content)
        assert payload["data"]["attributes"]["payment_method_types"] == ["gcash"]
        return httpx.Response(
            200,
            json={
                "data": {
                    "id": "cs_abc123",
                    "attributes": {"checkout_url": "https://pay.paymongo.com/checkout/cs_abc123"},
                }
            },
        )

    mock_client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url=settings.PAYMONGO_BASE_URL,
        headers={"Authorization": "Basic " + base64.b64encode(b"sk_test_x:").decode()},
    )
    from apps.rewards.drivers import PayMongoDriver

    monkeypatch.setattr(
        "apps.rewards.services.get_driver",
        lambda provider, client=None: PayMongoDriver(client=mock_client),
    )
    flyer = FlyerFactory(creator=user, reward_amount_cents=200000, reward_currency="PHP")
    resp = auth_client.post(
        "/api/rewards", {"flyer_id": str(flyer.pk), "provider": "gcash"}, format="json"
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["checkout_url"] == "https://pay.paymongo.com/checkout/cs_abc123"
    assert RewardTransaction.objects.get(pk=body["transaction_id"]).provider_reference == "cs_abc123"


def test_reward_status_permissions(auth_client, user):
    flyer = FlyerFactory(creator=user)
    tx = RewardTransaction.objects.create(
        flyer=flyer, user=user, provider="stripe", provider_reference="pi_x", amount_cents=1000
    )
    ok = auth_client.get(f"/api/rewards/{tx.pk}/status")
    assert ok.status_code == 200
    assert ok.json()["status"] == "pending"
    # stranger gets 403
    from apps.users.factories import UserFactory

    other = UserFactory()
    auth_client.force_authenticate(user=other)
    denied = auth_client.get(f"/api/rewards/{tx.pk}/status")
    assert denied.status_code == 403
    # unknown id 404
    auth_client.force_authenticate(user=user)
    assert auth_client.get(f"/api/rewards/{uuid.uuid4()}/status").status_code == 404


def test_stripe_webhook_signature_and_dedupe(api_client, monkeypatch):
    _mock_stripe(monkeypatch)
    flyer = FlyerFactory()
    tx = RewardTransaction.objects.create(
        flyer=flyer, user=flyer.creator, provider="stripe",
        provider_reference="cs_test_123", amount_cents=500000,
    )
    event = {"id": "evt_1", "type": "checkout.session.completed",
             "data": {"object": {"id": "cs_test_123"}}}
    monkeypatch.setattr(
        "stripe.Webhook.construct_event", lambda payload, sig, secret: event
    )
    resp = api_client.post(
        "/api/webhooks/stripe", data=json.dumps(event), content_type="application/json",
        headers={"Stripe-Signature": "t=1,v1=fake"},
    )
    assert resp.status_code == 200
    # eager celery processed it
    tx.refresh_from_db()
    assert tx.status == "succeeded"
    assert WebhookEvent.objects.filter(provider="stripe", event_id="evt_1").count() == 1
    # duplicate → still 200, no second row
    resp2 = api_client.post(
        "/api/webhooks/stripe", data=json.dumps(event), content_type="application/json",
        headers={"Stripe-Signature": "t=1,v1=fake"},
    )
    assert resp2.status_code == 200
    assert WebhookEvent.objects.filter(provider="stripe", event_id="evt_1").count() == 1


def test_stripe_webhook_bad_signature_400(api_client, monkeypatch):
    def bad(payload, sig, secret):
        raise ValueError("bad sig")

    monkeypatch.setattr("stripe.Webhook.construct_event", bad)
    resp = api_client.post(
        "/api/webhooks/stripe", data=b"{}", content_type="application/json",
        headers={"Stripe-Signature": "bad"},
    )
    assert resp.status_code == 400


def test_paymongo_webhook_hmac_verification(api_client, settings, monkeypatch):
    settings.PAYMONGO_WEBHOOK_SECRET = "whsec_test"
    flyer = FlyerFactory()
    tx = RewardTransaction.objects.create(
        flyer=flyer, user=flyer.creator, provider="gcash",
        provider_reference="cs_abc123", amount_cents=200000,
    )
    payload = json.dumps({
        "id": "evt_pm_1", "data": {"id": "cs_abc123", "type": "checkout_session.payment.paid",
                                   "attributes": {"id": "cs_abc123"}}
    }).encode()
    ts = "1700000000"
    sig = hmac.new(
        b"whsec_test", f"{ts}.{payload.decode()}".encode(), hashlib.sha256
    ).hexdigest()
    header = f"t={ts},te={sig}"
    resp = api_client.post(
        "/api/webhooks/paymongo", data=payload, content_type="application/json",
        headers={"Paymongo-Signature": header},
    )
    assert resp.status_code == 200
    tx.refresh_from_db()
    # event type not in success list → remains pending, but event recorded
    assert WebhookEvent.objects.filter(provider="gcash", event_id="evt_pm_1").exists()


def test_paymongo_webhook_bad_signature_400(api_client):
    resp = api_client.post(
        "/api/webhooks/paymongo", data=b"{}", content_type="application/json",
        headers={"Paymongo-Signature": "t=1,te=bad"},
    )
    assert resp.status_code == 400


def test_apply_provider_event_transitions(db):
    from apps.rewards.services import RewardService

    flyer = FlyerFactory()
    RewardTransaction.objects.create(
        flyer=flyer, user=flyer.creator, provider="stripe",
        provider_reference="pi_t", amount_cents=1000,
    )
    out = RewardService.apply_provider_event("stripe", "pi_t", "checkout.session.completed", {})
    assert out is not None and out.status == "succeeded"
    out = RewardService.apply_provider_event("stripe", "pi_t", "charge.refunded", {})
    assert out is not None and out.status == "refunded"
    assert RewardService.apply_provider_event("stripe", "missing", "checkout.session.completed", {}) is None
