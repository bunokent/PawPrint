"""Webhook services — signature verification + idempotent dedupe + fast dispatch."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from django.db import IntegrityError, transaction

from .models import WebhookEvent

logger = logging.getLogger(__name__)


class WebhookError(Exception):
    pass


class WebhookService:
    @staticmethod
    @transaction.atomic
    def record_and_dispatch(provider: str, event_id: str, event_type: str, payload: dict) -> bool:
        """Dedupe via (provider, event_id); dispatch Celery task on first sight.

        Returns True when the event is new (and was dispatched), False when duplicate.
        """
        try:
            WebhookEvent.objects.create(
                provider=provider, event_id=event_id, event_type=event_type, payload=payload
            )
        except IntegrityError:
            return False
        from .tasks import process_reward_webhook

        process_reward_webhook.delay(provider, event_id, event_type, payload)
        return True

    @staticmethod
    def mark_processed(provider: str, event_id: str) -> None:
        WebhookEvent.objects.filter(provider=provider, event_id=event_id).update(
            processed_at=datetime.now(UTC)
        )
