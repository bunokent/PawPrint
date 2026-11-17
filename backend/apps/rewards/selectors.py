"""Reward selectors."""

from __future__ import annotations

import uuid

from django.db.models import QuerySet

from .models import RewardTransaction


def select_transaction_queryset() -> QuerySet[RewardTransaction]:
    return RewardTransaction.objects.select_related("flyer", "user").only(
        "id", "provider", "provider_reference", "amount_cents", "currency", "status",
        "metadata", "created_at", "updated_at",
        "flyer__id", "flyer__creator_id", "user__id", "user__email",
    )


def get_transaction_by_id(tx_id: uuid.UUID) -> RewardTransaction | None:
    return select_transaction_queryset().filter(pk=tx_id).first()


def get_transaction_by_provider_ref(provider: str, reference: str) -> RewardTransaction | None:
    return select_transaction_queryset().filter(provider=provider, provider_reference=reference).first()


def list_transactions_for_user(user_id: uuid.UUID) -> QuerySet[RewardTransaction]:
    return select_transaction_queryset().filter(user_id=user_id).order_by("-created_at")
