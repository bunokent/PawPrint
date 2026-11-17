"""WebSocket routing — flyer generation events."""

from django.urls import path

from apps.flyers.consumers import FlyerConsumer

websocket_urlpatterns = [
    path("ws/flyers/", FlyerConsumer.as_asgi()),
]
