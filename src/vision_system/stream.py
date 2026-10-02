from __future__ import annotations

from collections import defaultdict
from threading import Condition, Lock
from time import monotonic


class CameraStreamHub:
    def __init__(self) -> None:
        self._frames: dict[str, bytes] = {}
        self._updated: dict[str, float] = defaultdict(float)
        self._condition = Condition(Lock())

    def publish(self, camera_id: str, jpeg: bytes) -> None:
        with self._condition:
            self._frames[camera_id] = jpeg
            self._updated[camera_id] = monotonic()
            self._condition.notify_all()

    def wait_for_frame(self, camera_id: str, after: float = 0.0, timeout: float = 5.0) -> tuple[bytes | None, float]:
        with self._condition:
            self._condition.wait_for(lambda: self._updated.get(camera_id, 0.0) > after, timeout=timeout)
            return self._frames.get(camera_id), self._updated.get(camera_id, 0.0)


stream_hub = CameraStreamHub()


def encode_annotated_frame(frame, tracks) -> bytes:
    import cv2
    output = frame.copy()
    for track in tracks:
        if track.missed_frames:
            continue
        box = track.bbox
        p1, p2 = (int(box.x1), int(box.y1)), (int(box.x2), int(box.y2))
        cv2.rectangle(output, p1, p2, (92, 225, 212), 2)
        label = f"{track.id}  {track.confidence:.0%}"
        cv2.putText(output, label, (p1[0] + 4, max(18, p1[1] - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (184, 238, 102), 1, cv2.LINE_AA)
    ok, encoded = cv2.imencode('.jpg', output, [cv2.IMWRITE_JPEG_QUALITY, 82])
    if not ok:
        raise RuntimeError('Failed to encode camera frame')
    return encoded.tobytes()


def mjpeg_stream(camera_id: str):
    last_update = 0.0
    while True:
        frame, last_update = stream_hub.wait_for_frame(camera_id, last_update)
        if frame is None:
            continue
        yield b'--frame\r\nContent-Type: image/jpeg\r\nCache-Control: no-cache\r\n\r\n' + frame + b'\r\n'
