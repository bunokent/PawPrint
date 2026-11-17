"""seed_demo — populate a realistic demo dataset (users, pets, flyers, rewards)."""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.flyers.models import Flyer
from apps.pets.models import Pet
from apps.users.models import User

DEMO_PASSWORD = "demo1234"


class Command(BaseCommand):
    help = "Seed demo users, pets, flyers and a reward transaction."

    def handle(self, *args: object, **options: object) -> None:
        owner, _ = User.objects.get_or_create(
            email="mia@example.com",
            defaults={"display_name": "Mia Santos", "phone": "+63 917 000 0001"},
        )
        owner.set_password(DEMO_PASSWORD)
        owner.save()
        shelter, _ = User.objects.get_or_create(
            email="shelter@example.com",
            defaults={"display_name": "Happy Tails Shelter", "phone": "+63 917 000 0002"},
        )
        shelter.set_password(DEMO_PASSWORD)
        shelter.save()

        bruno = Pet.objects.create(
            owner=owner, name="Bruno", species=Pet.Species.DOG, breed="Aspin",
            color="Brown brindle", age=3, temperament_tags=["playful", "gentle"],
            health_tags=["vaccinated", "neutered"], status=Pet.Status.LOST,
        )
        luna = Pet.objects.create(
            owner=shelter, name="Luna", species=Pet.Species.CAT, breed="Domestic shorthair",
            color="Orange tabby", age=1, temperament_tags=["cuddly", "calm"],
            health_tags=["vaccinated", "spayed"], status=Pet.Status.ADOPTABLE,
        )

        Flyer.objects.create(
            pet=bruno, creator=owner, mode=Flyer.Mode.EMERGENCY,
            last_seen_location="Brgy. Poblacion, Makati", last_seen_date=timezone.now(),
            distinctive_markings="White patch on chest, torn left ear",
            contact_phone=owner.phone, contact_email=owner.email,
            reward_enabled=True, reward_amount_cents=500000, reward_currency="PHP",
            qr_target_value="http://localhost:5173/flyers/__demo__", status=Flyer.Status.ACTIVE,
        )
        Flyer.objects.create(
            pet=luna, creator=shelter, mode=Flyer.Mode.OUTREACH,
            distinctive_markings="Loves window perches and slow blinks",
            contact_phone=shelter.phone, contact_email=shelter.email,
            qr_target_value="http://localhost:5173/flyers/__demo__", status=Flyer.Status.ACTIVE,
        )
        self.stdout.write(self.style.SUCCESS("Seeded demo data (login: mia@example.com / demo1234)"))
