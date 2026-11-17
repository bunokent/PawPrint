"""Unit: QrService."""

from apps.flyers.qr import QrService


def test_target_url():
    assert QrService.target_url("abc", "http://localhost:5173/") == "http://localhost:5173/flyers/abc"


def test_svg_for_url():
    svg = QrService.svg_for_url("http://localhost:5173/flyers/abc")
    assert svg.startswith("<svg") or "<svg" in svg[:200]


def test_png_bytes_for_url():
    png = QrService.png_bytes_for_url("http://localhost:5173/flyers/abc")
    assert png.startswith(b"\x89PNG")
