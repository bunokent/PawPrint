"""Reward views — thin."""

from __future__ import annotations

import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from .selectors import get_transaction_by_id, list_transactions_for_user
from .serializers import RewardCreateSerializer, RewardInitSerializer, RewardStatusSerializer
from .services import RewardError, RewardService


class RewardCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RewardCreateSerializer, responses={201: RewardInitSerializer})
    def post(self, request: Request) -> Response:
        serializer = RewardCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            init = RewardService.create_reward(request.user, **serializer.validated_data)
        except RewardError as exc:
            return Response({"error": {"code": "reward_error", "message": str(exc)}}, status=400)
        tx = init.transaction
        return Response(
            RewardInitSerializer(
                {
                    "transaction_id": tx.pk, "provider": tx.provider, "status": tx.status,
                    "amount_cents": tx.amount_cents, "currency": tx.currency,
                    "checkout_url": init.checkout_url, "qr_payload": init.qr_payload,
                }
            ).data,
            status=status.HTTP_201_CREATED,
        )


class RewardStatusView(APIView):
    """Poll payment status — payer or flyer creator only."""

    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: RewardStatusSerializer})
    def get(self, request: Request, pk: uuid.UUID) -> Response:
        tx = get_transaction_by_id(pk)
        if tx is None:
            return Response({"error": {"code": "not_found", "message": "Transaction not found."}}, status=404)
        if tx.user_id != request.user.pk and tx.flyer.creator_id != request.user.pk:
            return Response({"error": {"code": "forbidden", "message": "Not allowed."}}, status=403)
        return Response(RewardStatusSerializer(tx).data)


class MyRewardsView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: RewardStatusSerializer(many=True)})
    def get(self, request: Request) -> Response:
        user_id = request.user.pk
        assert user_id is not None
        txs = list_transactions_for_user(user_id)
        return Response(RewardStatusSerializer(txs, many=True).data)
