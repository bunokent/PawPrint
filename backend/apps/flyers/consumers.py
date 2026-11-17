"""WebSocket consumer — broadcasts flyer.generated events to the 'flyers' group."""

from __future__ import annotations

import logging

from channels.generic.websocket import AsyncJsonWebsocketConsumer

logger = logging.getLogger(__name__)


class FlyerConsumer(AsyncJsonWebsocketConsumer):
    group_name = "flyers"

    async def connect(self) -> None:
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code: int) -> None:
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def flyer_generated(self, event: dict) -> None:
        await self.send_json({"type": "flyer.generated", "flyer_id": event["flyer_id"],
                              "export_png_url": event.get("export_png_url", ""),
                              "export_pdf_url": event.get("export_pdf_url", "")})


def broadcast_flyer_generated(flyer_id: str, export_png_url: str, export_pdf_url: str) -> None:
    """Sync helper used by the Celery task to notify connected clients."""
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    async_to_sync(get_channel_layer().group_send)(
        "flyers",
        {
            "type": "flyer.generated",
            "flyer_id": flyer_id,
            "export_png_url": export_png_url,
            "export_pdf_url": export_pdf_url,
        },
    )
