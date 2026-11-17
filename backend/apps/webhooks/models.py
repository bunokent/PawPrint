"""WebhookEvent — idempotency ledger for provider webhooks."""

import uuid

from django.db import models
from django.db.models import UniqueConstraint


class WebhookEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.CharField(max_length=16)
    event_id = models.CharField(max_length=255)
    event_type = models.CharField(max_length=128)
    payload = models.JSONField(default=dict)
    processed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "webhooks_webhookevent"
        constraints = [
            UniqueConstraint(fields=["provider", "event_id"], name="webhook_provider_event_unique")
        ]
        indexes = [models.Index(fields=["provider", "created_at"], name="webhook_provider_created_idx")]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_id}"
