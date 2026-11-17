"""Reward tasks (queue: webhooks)."""

from __future__ import annotations

from celery import shared_task


@shared_task(name="apps.rewards.tasks.sync_transaction_status")
def sync_transaction_status(tx_id: str, provider_reference: str, event_type: str) -> str:

    from apps.rewards.services import RewardService

    tx = RewardService.apply_provider_event(
        provider="stripe", provider_reference=provider_reference, event_type=event_type, payload={}
    )
    return tx.status if tx else "missing"
