"""DTOs for the vision gatekeeper."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DetectionResult:
    passed: bool
    pet_classes: list[str] = field(default_factory=list)
    detected_classes: list[str] = field(default_factory=list)
    max_confidence: float = 0.0
