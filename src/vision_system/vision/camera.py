from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator


@dataclass(frozen=True)
class Frame:
    image: object
    index: int
    timestamp: float


class VideoSource:
    """OpenCV video/webcam source with explicit lifecycle management."""

    def __init__(self, source: str | int, width: int | None = None, height: int | None = None) -> None:
        self.source = int(source) if isinstance(source, str) and source.isdigit() else source
        self.width = width
        self.height = height
        self._capture = None

    def __enter__(self) -> "VideoSource":
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("Video input requires the vision extra: pip install -e '.[vision]'") from exc
        self._capture = cv2.VideoCapture(self.source)
        if not self._capture.isOpened():
            raise RuntimeError(f"Unable to open video source: {self.source}")
        if self.width:
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        if self.height:
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        return self

    def __exit__(self, *_: object) -> None:
        if self._capture is not None:
            self._capture.release()

    def frames(self) -> Iterator[Frame]:
        if self._capture is None:
            raise RuntimeError("VideoSource must be used as a context manager")
        import time
        index = 0
        while True:
            ok, image = self._capture.read()
            if not ok:
                break
            yield Frame(image=image, index=index, timestamp=time.time())
            index += 1
