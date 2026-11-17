import factory

from .models import WebhookEvent


class WebhookEventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WebhookEvent

    provider = "stripe"
    event_id = factory.Sequence(lambda n: f"evt_{n}")
    event_type = "checkout.session.completed"
    payload = factory.LazyFunction(dict)
