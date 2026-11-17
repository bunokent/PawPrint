import factory

from apps.users.factories import UserFactory

from .models import Pet


class PetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Pet

    owner = factory.SubFactory(UserFactory)
    name = factory.Faker("first_name")
    species = Pet.Species.DOG
    breed = factory.Faker("word")
    color = factory.Faker("color_name")
    temperament_tags = ["friendly"]
    health_tags = ["vaccinated"]
    status = Pet.Status.ADOPTABLE
