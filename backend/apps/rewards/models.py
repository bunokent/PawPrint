"""RewardTransaction — one row per reward funding attempt (Stripe test / GCash / QR Ph)."""

import uuid

from django.db import models
from django.db.models import CheckConstraint, Index, Q, UniqueConstraint


class RewardTransaction(models.Model):
    class Provider(models.TextChoices):
        STRIPE = "stripe", "Stripe (test mode)"
        GCASH = "gcash", "GCash (PayMongo)"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    flyer = models.ForeignKey("flyers.Flyer", on_delete=models.CASCADE, related_name="reward_transactions")
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, related_name="reward_transactions")
    provider = models.CharField(max_length=16, choices=Provider.choices)
    provider_reference = models.CharField(max_length=255, unique=True)
    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=8, default="PHP")
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rewards_rewardtransaction"
        constraints = [
            UniqueConstraint(fields=["provider", "provider_reference"], name="reward_provider_ref_unique"),
            CheckConstraint(condition=Q(amount_cents__gt=0), name="reward_amount_positive"),
        ]
        indexes = [
            Index(fields=["user", "created_at"], name="reward_user_created_idx"),
            Index(fields=["flyer", "status"], name="reward_flyer_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.provider} {self.amount_cents} {self.currency} ({self.status})"
