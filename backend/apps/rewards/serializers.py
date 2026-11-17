"""Reward serializers."""

from __future__ import annotations

from rest_framework import serializers

from .models import RewardTransaction


class RewardCreateSerializer(serializers.Serializer):
    flyer_id = serializers.UUIDField()
    provider = serializers.ChoiceField(choices=[RewardTransaction.Provider.STRIPE, RewardTransaction.Provider.GCASH])
    amount_cents = serializers.IntegerField(min_value=1, required=False)
    currency = serializers.CharField(max_length=8, required=False)


class RewardInitSerializer(serializers.Serializer):
    transaction_id = serializers.UUIDField()
    provider = serializers.CharField()
    status = serializers.CharField()
    amount_cents = serializers.IntegerField()
    currency = serializers.CharField()
    checkout_url = serializers.CharField(allow_blank=True)
    qr_payload = serializers.CharField(allow_blank=True)


class RewardStatusSerializer(serializers.ModelSerializer[RewardTransaction]):
    class Meta:
        model = RewardTransaction
        fields = ["id", "provider", "status", "amount_cents", "currency", "provider_reference", "created_at"]
