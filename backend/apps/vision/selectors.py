"""Vision selectors — read side of detection logs."""

from __future__ import annotations

import uuid

from django.db.models import QuerySet

from .models import PetDetectionLog


def select_detection_log_queryset() -> QuerySet[PetDetectionLog]:
    return PetDetectionLog.objects.select_related("user").only(
        "id", "detected_classes", "max_confidence", "passed", "created_at", "user__id"
    )


def get_log_by_id(log_id: uuid.UUID) -> PetDetectionLog | None:
    return select_detection_log_queryset().filter(pk=log_id).first()


def list_logs_for_user(user_id: uuid.UUID) -> QuerySet[PetDetectionLog]:
    return select_detection_log_queryset().filter(user_id=user_id).order_by("-created_at")
