"""Public webhook endpoints — CSRF-exempt, signature-verified, dedupe, 200 in <50ms."""

from __future__ import annotations

import logging

from django.http import HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt

from apps.rewards.drivers import get_driver

from .services import WebhookService

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            event = get_driver("stripe").verify_webhook(
                request.body, request.headers.get("Stripe-Signature")
            )
        except Exception:
            logger.warning("stripe webhook signature rejected")
            return HttpResponse(status=400)
        WebhookService.record_and_dispatch(
            provider="stripe",
            event_id=str(event.get("id", "")),
            event_type=str(event.get("type", "")),
            payload=event,
        )
        return HttpResponse(status=200)


@method_decorator(csrf_exempt, name="dispatch")
class PayMongoWebhookView(View):
    def post(self, request: HttpRequest) -> HttpResponse:
        try:
            event = get_driver("gcash").verify_webhook(
                request.body, request.headers.get("Paymongo-Signature")
            )
        except Exception:
            logger.warning("paymongo webhook signature rejected")
            return HttpResponse(status=400)
        data = event.get("data", {})
        WebhookService.record_and_dispatch(
            provider="gcash",
            event_id=str(event.get("id", "")),
            event_type=str(data.get("type", "")),
            payload=event,
        )
        return HttpResponse(status=200)
