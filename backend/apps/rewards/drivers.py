"""Payment drivers — PaymentDriver protocol, StripeDriver (test mode), PayMongoDriver (GCash/QR Ph)."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx
import stripe
from django.conf import settings

from .models import RewardTransaction


@dataclass(frozen=True)
class DriverResult:
    provider_reference: str
    checkout_url: str = ""
    qr_payload: str = ""
    raw: dict[str, Any] = field(default_factory=dict)


class PaymentDriver(Protocol):
    name: str

    def create_payment(self, tx: RewardTransaction, return_url: str, cancel_url: str) -> DriverResult: ...

    def verify_webhook(self, payload: bytes, signature_header: str | None) -> dict[str, Any]: ...


class StripeDriver:
    """Stripe Checkout Session in TEST mode."""

    name: str = RewardTransaction.Provider.STRIPE

    def __init__(self) -> None:
        stripe.api_key = settings.STRIPE_SECRET_KEY

    def create_payment(self, tx: RewardTransaction, return_url: str, cancel_url: str) -> DriverResult:
        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=return_url,
            cancel_url=cancel_url,
            line_items=[
                {
                    "price_data": {
                        "currency": tx.currency.lower(),
                        "unit_amount": tx.amount_cents,
                        "product_data": {"name": f"Reward for lost pet flyer {tx.flyer_id}"},
                    },
                    "quantity": 1,
                }
            ],
            metadata={"reward_transaction_id": str(tx.pk), "flyer_id": str(tx.flyer_id)},
        )
        return DriverResult(
            provider_reference=str(session.id),
            checkout_url=str(session.url),
            raw={"session_id": session.id},
        )

    def verify_webhook(self, payload: bytes, signature_header: str | None) -> dict[str, Any]:
        event = stripe.Webhook.construct_event(
            payload, signature_header or "", settings.STRIPE_WEBHOOK_SECRET
        )
        return dict(event)


class PayMongoDriver:
    """PayMongo REST: GCash Checkout Session or QR Ph Payment Intent."""

    name: str = RewardTransaction.Provider.GCASH

    def __init__(self, client: httpx.Client | None = None) -> None:
        self._client = client or httpx.Client(
            base_url=settings.PAYMONGO_BASE_URL,
            headers={"Authorization": "Basic " + base64.b64encode(
                f"{settings.PAYMONGO_SECRET_KEY}:".encode()).decode()},
            timeout=15,
        )

    def create_payment(self, tx: RewardTransaction, return_url: str, cancel_url: str) -> DriverResult:
        if tx.provider == RewardTransaction.Provider.GCASH:
            resp = self._client.post(
                "/v1/checkout_sessions",
                json={
                    "data": {
                        "attributes": {
                            "description": f"Reward for flyer {tx.flyer_id}",
                            "line_items": [
                                {
                                    "name": "Pet reward",
                                    "amount": tx.amount_cents,
                                    "currency": tx.currency.upper(),
                                    "quantity": 1,
                                }
                            ],
                            "payment_method_types": ["gcash"],
                            "success_url": return_url,
                            "cancel_url": cancel_url,
                            "metadata": {"reward_transaction_id": str(tx.pk)},
                        }
                    }
                },
            )
            resp.raise_for_status()
            data = resp.json()["data"]
            return DriverResult(
                provider_reference=data["id"],
                checkout_url=data["attributes"]["checkout_url"],
                raw=data,
            )
        raise ValueError(f"Unsupported provider for PayMongoDriver: {tx.provider}")

    def create_qrph_payment(self, tx: RewardTransaction) -> DriverResult:
        """QR Ph: create a PaymentIntent, attach a qrph PaymentMethod, return the QR payload."""
        intent_resp = self._client.post(
            "/v1/payment_intents",
            json={
                "data": {
                    "attributes": {
                        "amount": tx.amount_cents,
                        "currency": tx.currency.upper(),
                        "payment_method_allowed": ["qrph"],
                        "description": f"Reward for flyer {tx.flyer_id}",
                        "metadata": {"reward_transaction_id": str(tx.pk)},
                    }
                }
            },
        )
        intent_resp.raise_for_status()
        intent = intent_resp.json()["data"]
        method_resp = self._client.post(
            "/v1/payment_methods",
            json={
                "data": {
                    "attributes": {
                        "type": "qrph",
                        "billing": {"name": tx.user.display_name or tx.user.email, "email": tx.user.email},
                    }
                }
            },
        )
        method_resp.raise_for_status()
        method = method_resp.json()["data"]
        attach_resp = self._client.post(
            f"/v1/payment_intents/{intent['id']}/attach",
            json={
                "data": {
                    "attributes": {
                        "payment_method": method["id"],
                        "client_key": intent["attributes"].get("client_key", ""),
                    }
                }
            },
        )
        attach_resp.raise_for_status()
        attached = attach_resp.json()["data"]
        qr_payload = attached["attributes"].get("qr_code_string", "") or json.dumps(attached["attributes"])
        return DriverResult(provider_reference=intent["id"], qr_payload=qr_payload, raw=attached)

    def verify_webhook(self, payload: bytes, signature_header: str | None) -> dict[str, Any]:
        """PayMongo webhook signature: HMAC-SHA256 of '{timestamp}.{payload}' sent as te=..."""
        import hashlib
        import hmac

        if not signature_header:
            raise ValueError("Missing PayMongo-Signature header")
        parts = dict(part.split("=", 1) for part in signature_header.split(",") if "=" in part)
        timestamp = parts.get("t", "")
        expected = parts.get("te", "")
        signed = f"{timestamp}.{payload.decode('utf-8')}".encode()
        digest = hmac.new(settings.PAYMONGO_WEBHOOK_SECRET.encode(), signed, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest, expected):
            raise ValueError("Invalid PayMongo webhook signature")
        return json.loads(payload)


def get_driver(provider: str, client: httpx.Client | None = None) -> PaymentDriver:
    if provider == RewardTransaction.Provider.STRIPE:
        return StripeDriver()
    if provider == RewardTransaction.Provider.GCASH:
        return PayMongoDriver(client=client)
    raise ValueError(f"Unknown provider: {provider}")
