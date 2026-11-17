"""Webhook processing tasks (queue: webhooks)."""

from __future__ import annotations

from celery import shared_task

from .services import WebhookService


@shared_task(name="apps.webhooks.tasks.process_reward_webhook")
def process_reward_webhook(provider: str, event_id: str, event_type: str, payload: dict) -> str:
    from apps.rewards.services import RewardService

    data = payload.get("data", payload)
    attributes = data.get("attributes", {}) if isinstance(data, dict) else {}
    object_data = data.get("object", {}) if isinstance(data, dict) else {}
    reference = (
        attributes.get("id")
        or object_data.get("id")
        or attributes.get("payment_intent")
        or payload.get("id")
        or ""
    )
    tx = RewardService.apply_provider_event(
        provider=provider, provider_reference=str(reference), event_type=event_type, payload=payload
    )
    WebhookService.mark_processed(provider, event_id)
    return tx.status if tx else "unknown"
