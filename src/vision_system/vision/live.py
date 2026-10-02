from __future__ import annotations

from .camera import VideoSource
from .detector import PersonDetector
from .tracker import IoUTracker
from ..stream import encode_annotated_frame, stream_hub


def run_live(source: str | int, camera_id: str, detector: PersonDetector, tracker: IoUTracker) -> None:
    with VideoSource(source) as video:
        for frame in video.frames():
            detections = detector.detect(frame.image)
            tracks = tracker.update(detections)
            stream_hub.publish(camera_id, encode_annotated_frame(frame.image, tracks))
