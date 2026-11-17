"""RewardService — atomic creation + webhook application with idempotency."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.db import transaction

from apps.flyers.selectors import get_flyer_by_id

from .drivers import DriverResult, get_driver
from .models import RewardTransaction
from .selectors import get_transaction_by_provider_ref

logger = logging.getLogger(__name__)


class RewardError(Exception):
    pass


@dataclass(frozen=True)
class RewardInit:
    transaction: RewardTransaction
    checkout_url: str
    qr_payload: str


class RewardService:
    @staticmethod
    @transaction.atomic
    def create_reward(user, flyer_id: uuid.UUID, provider: str, amount_cents: int | None = None,
                      currency: str | None = None) -> RewardInit:
        """Create a pending RewardTransaction and delegate to the payment driver."""
        flyer = get_flyer_by_id(flyer_id)
        if flyer is None:
            raise RewardError("Flyer not found.")
        amount = amount_cents if amount_cents is not None else flyer.reward_amount_cents
        if amount <= 0:
            raise RewardError("A positive reward amount is required.")
        cur = (currency or flyer.reward_currency or "PHP").upper()
        with transaction.atomic():
            tx = RewardTransaction.objects.create(
                flyer=flyer, user=user, provider=provider,
                provider_reference=f"pending-{uuid.uuid4()}",
                amount_cents=amount, currency=cur, status=RewardTransaction.Status.PENDING,
            )
        return_url = f"{settings.FRONTEND_BASE_URL}/rewards/success?tx={tx.pk}"
        cancel_url = f"{settings.FRONTEND_BASE_URL}/rewards/cancel?tx={tx.pk}"
        driver = get_driver(provider)
        result: DriverResult = driver.create_payment(tx, return_url, cancel_url)
        RewardTransaction.objects.filter(pk=tx.pk).update(
            provider_reference=result.provider_reference, metadata=result.raw
        )
        tx.refresh_from_db()
        return RewardInit(transaction=tx, checkout_url=result.checkout_url, qr_payload=result.qr_payload)

    @staticmethod
    @transaction.atomic
    def apply_provider_event(provider: str, provider_reference: str, event_type: str,
                             payload: dict) -> RewardTransaction | None:
        """Idempotently apply a provider event to its transaction (select_for_update)."""
        tx = get_transaction_by_provider_ref(provider, provider_reference)
        if tx is None:
            logger.warning("webhook for unknown reference %s/%s", provider, provider_reference)
            return None
        RewardTransaction.objects.select_for_update().filter(pk=tx.pk)
        if event_type in ("checkout.session.completed", "payment_intent.succeeded", "charge.succeeded"):
            new_status = RewardTransaction.Status.SUCCEEDED
        elif event_type in ("checkout.session.expired", "payment_intent.payment_failed"):
            new_status = RewardTransaction.Status.FAILED
        elif event_type in ("charge.refunded",):
            new_status = RewardTransaction.Status.REFUNDED
        else:
            return tx
        RewardTransaction.objects.filter(pk=tx.pk).update(status=new_status)
        tx.refresh_from_db()
        return tx
