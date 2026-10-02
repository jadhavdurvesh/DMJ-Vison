from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Iterable
from uuid import uuid4


@dataclass(frozen=True)
class BoundingBox:
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


def iou(a: BoundingBox, b: BoundingBox) -> float:
    ix1, iy1 = max(a.x1, b.x1), max(a.y1, b.y1)
    ix2, iy2 = min(a.x2, b.x2), min(a.y2, b.y2)
    intersection = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
    union = a.area + b.area - intersection
    return intersection / union if union else 0.0


@dataclass
class Detection:
    bbox: BoundingBox
    confidence: float
    class_id: int = 0


@dataclass
class Track:
    id: str
    bbox: BoundingBox
    confidence: float
    missed_frames: int = 0
    age: int = 1


class IoUTracker:
    """Small dependency-free tracker for person detections.

    IDs are local operational identifiers. They are intentionally not tied to
    names, faces, biometric templates, or other identity attributes.
    """

    def __init__(self, iou_threshold: float = 0.30, max_missed_frames: int = 20) -> None:
        if not 0 <= iou_threshold <= 1:
            raise ValueError("iou_threshold must be between 0 and 1")
        if max_missed_frames < 0:
            raise ValueError("max_missed_frames must be non-negative")
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self._tracks: dict[str, Track] = {}

    @property
    def tracks(self) -> tuple[Track, ...]:
        return tuple(self._tracks.values())

    def update(self, detections: Iterable[Detection]) -> list[Track]:
        detections = list(detections)
        unmatched_tracks = set(self._tracks)
        unmatched_detections = set(range(len(detections)))
        matches: list[tuple[str, int, float]] = []

        # Greedy highest-IoU assignment is deterministic and sufficient for the
        # lightweight edge-worker MVP. A stronger tracker can replace this class.
        candidates = sorted(
            ((iou(track.bbox, detection.bbox), track_id, index)
             for track_id, track in self._tracks.items()
             for index, detection in enumerate(detections)),
            reverse=True,
        )
        for overlap, track_id, index in candidates:
            if overlap < self.iou_threshold or track_id not in unmatched_tracks or index not in unmatched_detections:
                continue
            matches.append((track_id, index, overlap))
            unmatched_tracks.remove(track_id)
            unmatched_detections.remove(index)

        for track_id, index, _ in matches:
            detection = detections[index]
            track = self._tracks[track_id]
            track.bbox = detection.bbox
            track.confidence = detection.confidence
            track.missed_frames = 0
            track.age += 1

        for track_id in unmatched_tracks:
            self._tracks[track_id].missed_frames += 1
            self._tracks[track_id].age += 1

        for index in unmatched_detections:
            detection = detections[index]
            track_id = f"trk_{uuid4().hex[:8]}"
            self._tracks[track_id] = Track(track_id, detection.bbox, detection.confidence)

        expired = [track_id for track_id, track in self._tracks.items() if track.missed_frames > self.max_missed_frames]
        for track_id in expired:
            del self._tracks[track_id]

        return sorted(self._tracks.values(), key=lambda track: track.id)
