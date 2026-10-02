from __future__ import annotations

import argparse

from ..repository import VisionRepository
from .detector import DetectorConfig, PersonDetector
from .pipeline import PipelineConfig, VisionPipeline
from .tracker import IoUTracker


def main() -> None:
    parser = argparse.ArgumentParser(description="DMJ Vision real-time camera worker")
    parser.add_argument("--source", default="0", help="Webcam index or video/RTSP URL")
    parser.add_argument("--camera-id", default="camera-1")
    parser.add_argument("--zone-id", default="default")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--device", default=None, help="Inference device, e.g. cpu or cuda:0")
    args = parser.parse_args()

    repository = VisionRepository()
    pipeline = VisionPipeline(
        PersonDetector(DetectorConfig(model=args.model, confidence=args.confidence, device=args.device)),
        IoUTracker(),
        PipelineConfig(camera_id=args.camera_id, zone_id=args.zone_id),
    )

    def handle(_, observation):
        track = repository.create_observation(observation)
        print(f"{track.id} | {observation.camera_id} | {observation.zone_id} | {observation.confidence:.2f}")

    pipeline.run(args.source, handle)


if __name__ == "__main__":
    main()
