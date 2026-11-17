"""Permission classes."""

from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView


class IsOwnerOrReadOnly(BasePermission):
    """Object-level: safe methods for anyone; mutations only for the object's creator/owner."""

    def has_object_permission(self, request: Request, view: APIView, obj: object) -> bool:
        if request.method in SAFE_METHODS:
            return True
        owner = getattr(obj, "creator", None) or getattr(obj, "owner", None)
        return owner is not None and owner == request.user
