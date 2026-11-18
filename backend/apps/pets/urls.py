from django.urls import path

from .views import PetCreateView, PhotoUploadView

urlpatterns = [
    path("photos", PhotoUploadView.as_view(), name="pet-photo-upload"),
    path("", PetCreateView.as_view(), name="pet-create"),
]
