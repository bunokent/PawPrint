import factory

from apps.flyers.factories import FlyerFactory
from apps.users.factories import UserFactory

from .models import RewardTransaction


class RewardTransactionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RewardTransaction

    flyer = factory.SubFactory(FlyerFactory)
    user = factory.SubFactory(UserFactory)
    provider = RewardTransaction.Provider.STRIPE
    provider_reference = factory.Sequence(lambda n: f"pi_test_{n}")
    amount_cents = 100000
    currency = "PHP"
    status = RewardTransaction.Status.PENDING
