"""QrService — renders QR codes (SVG for print fidelity) targeting the public flyer URL."""

from __future__ import annotations

import io

import qrcode
from qrcode.image.svg import SvgPathImage


class QrService:
    @staticmethod
    def target_url(flyer_id: str, base_url: str) -> str:
        return f"{base_url.rstrip('/')}/flyers/{flyer_id}"

    @staticmethod
    def svg_for_url(url: str, box_size: int = 10) -> str:
        """Crisp vector QR — ideal for A4@300dpi print exports."""
        qr = qrcode.QRCode(box_size=box_size, border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=SvgPathImage)
        buffer = io.BytesIO()
        img.save(buffer)
        return buffer.getvalue().decode("utf-8")

    @staticmethod
    def png_bytes_for_url(url: str, box_size: int = 10) -> bytes:
        qr = qrcode.QRCode(box_size=box_size, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
