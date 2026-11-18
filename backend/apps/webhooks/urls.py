from django.urls import path

from .views import PayMongoWebhookView, StripeWebhookView

urlpatterns = [
    path("stripe", StripeWebhookView.as_view(), name="webhook-stripe"),
    path("paymongo", PayMongoWebhookView.as_view(), name="webhook-paymongo"),
]
