import factory
from django.contrib.auth.hashers import make_password

from .models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    display_name = factory.Faker("name")
    password = factory.LazyFunction(lambda: make_password("testpass123"))
