import factory

from apps.pets.factories import PetFactory

from .models import Flyer


class FlyerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Flyer

    pet = factory.SubFactory(PetFactory)
    creator = factory.SelfAttribute("pet.owner")
    mode = Flyer.Mode.EMERGENCY
    status = Flyer.Status.ACTIVE
    contact_email = factory.Faker("email")
    qr_target_value = factory.Faker("url")
