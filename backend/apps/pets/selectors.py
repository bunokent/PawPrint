"""Pet selectors — optimized read QuerySets."""

from __future__ import annotations

import uuid

from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, QuerySet

from .models import Pet


def select_pet_queryset() -> QuerySet[Pet]:
    return (
        Pet.objects.select_related("owner")
        .only(
            "id", "name", "species", "breed", "color", "age", "temperament_tags",
            "health_tags", "photo_path", "status", "created_at",
            "owner__id", "owner__display_name", "owner__avatar_path",
        )
    )


def get_pet_by_id(pet_id: uuid.UUID) -> Pet | None:
    return select_pet_queryset().filter(pk=pet_id).first()


def search_pets(query: str, status: str | None = None) -> QuerySet[Pet]:
    """Full-text search via SearchVector + GIN index (never icontains scans)."""
    qs = select_pet_queryset()
    if status:
        qs = qs.filter(status=status)
    if query:
        search_query = SearchQuery(query, config="english")
        qs = (
            qs.filter(search_vector=search_query)
            .annotate(rank=SearchRank(F("search_vector"), search_query))
            .order_by("-rank", "-created_at")
        )
    return qs
