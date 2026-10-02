from __future__ import annotations

import argparse
import json
import urllib.parse
import urllib.request

from .detector import DetectorConfig, PersonDetector
from .pipeline import PipelineConfig, VisionPipeline
from .tracker import IoUTracker


def _post_observation(api_url: str, track_id: str, observation) -> dict:
    query = urllib.parse.urlencode({"track_id": track_id})
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/api/observations?{query}",
        data=json.dumps(observation.model_dump(mode="json")).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read())


def main() -> None:
    parser = argparse.ArgumentParser(description="DMJ Vision real-time camera worker")
    parser.add_argument("--source", default="0", help="Webcam index or video/RTSP URL")
    parser.add_argument("--camera-id", default="north-entry")
    parser.add_argument("--zone-id", default="entry")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--device", default=None, help="Inference device, e.g. cpu or cuda:0")
    parser.add_argument("--publish-every", type=int, default=5, help="Publish telemetry every N processed frames")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000", help="DMJ Vision API base URL")
    args = parser.parse_args()

    pipeline = VisionPipeline(
        PersonDetector(DetectorConfig(model=args.model, confidence=args.confidence, device=args.device)),
        IoUTracker(),
        PipelineConfig(camera_id=args.camera_id, zone_id=args.zone_id, publish_every=args.publish_every),
    )

    def handle(track, observation):
        result = _post_observation(args.api_url, track.id, observation)
        print(f"{result['id']} | {observation.camera_id} | {observation.zone_id} | {observation.confidence:.2f}")

    pipeline.run(args.source, handle)


if __name__ == "__main__":
    main()
