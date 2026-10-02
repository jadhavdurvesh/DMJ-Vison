from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from ..models import Observation
from .camera import Frame, VideoSource
from .detector import PersonDetector
from .tracker import IoUTracker, Track


@dataclass(frozen=True)
class PipelineConfig:
    camera_id: str
    zone_id: str = "unknown"
    display: bool = False
    direction: str | None = None
    publish_every: int = 5


class VisionPipeline:
    def __init__(self, detector: PersonDetector, tracker: IoUTracker, config: PipelineConfig) -> None:
        if config.publish_every < 1:
            raise ValueError("publish_every must be at least 1")
        self.detector = detector
        self.tracker = tracker
        self.config = config

    def process(self, frame: Frame) -> list[tuple[Track, Observation]]:
        detections = self.detector.detect(frame.image)
        tracks = self.tracker.update(detections)
        if frame.index % self.config.publish_every != 0:
            return []
        observed_at = datetime.fromtimestamp(frame.timestamp, tz=timezone.utc)
        events: list[tuple[Track, Observation]] = []
        for track in tracks:
            if track.missed_frames:
                continue
            events.append((track, Observation(
                camera_id=self.config.camera_id,
                zone_id=self.config.zone_id,
                observed_at=observed_at,
                confidence=track.confidence,
                direction=self.config.direction,
                quality=1.0,
            )))
        return events

    def run(self, source: str | int, on_observation: Callable[[Track, Observation], None]) -> None:
        with VideoSource(source) as video:
            for frame in video.frames():
                for track, observation in self.process(frame):
                    on_observation(track, observation)
