from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tracker import BoundingBox, Detection


@dataclass(frozen=True)
class DetectorConfig:
    model: str = "yolo11n.pt"
    confidence: float = 0.35
    device: str | None = None


class PersonDetector:
    """Ultralytics-backed person detector loaded lazily on first inference."""

    PERSON_CLASS = 0

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self._model: Any = None

    def _load(self) -> None:
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "Real detection requires the vision extra: pip install -e '.[vision]'"
            ) from exc
        self._model = YOLO(self.config.model)

    def detect(self, frame: Any) -> list[Detection]:
        self._load()
        kwargs: dict[str, Any] = {"conf": self.config.confidence, "classes": [self.PERSON_CLASS], "verbose": False}
        if self.config.device:
            kwargs["device"] = self.config.device
        result = self._model.predict(frame, **kwargs)[0]
        boxes = result.boxes
        detections: list[Detection] = []
        if boxes is None:
            return detections
        for xyxy, confidence, class_id in zip(boxes.xyxy.tolist(), boxes.conf.tolist(), boxes.cls.tolist()):
            detections.append(Detection(
                bbox=BoundingBox(*map(float, xyxy)),
                confidence=float(confidence),
                class_id=int(class_id),
            ))
        return detections
