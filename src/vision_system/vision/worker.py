from __future__ import annotations

import argparse
import json
import os
import threading
import time
import urllib.parse
import urllib.request

from ..stream import encode_annotated_frame
from .camera import VideoSource
from .detector import DetectorConfig, PersonDetector
from .tracker import IoUTracker


def _request(api_url: str, path: str, payload: bytes | None, content_type: str, token: str | None):
    headers = {"Content-Type": content_type}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{api_url.rstrip('/')}{path}", data=payload, headers=headers, method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.read()


def _heartbeat(api_url: str, camera_id: str, worker_id: str, name: str, location: str, token: str | None) -> None:
    path = "/api/workers/heartbeat?" + urllib.parse.urlencode({"name": name, "location": location})
    body = json.dumps({"worker_id": worker_id, "camera_id": camera_id}).encode()
    _request(api_url, path, body, "application/json", token)


def _heartbeat_loop(api_url: str, camera_id: str, worker_id: str, name: str, location: str, token: str | None, interval: int) -> None:
    while True:
        try:
            _heartbeat(api_url, camera_id, worker_id, name, location, token)
        except Exception as exc:
            print(f"heartbeat error: {exc}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="DMJ Vision real-time camera worker")
    parser.add_argument("--source", default="0", help="Webcam index, video file, or RTSP URL")
    parser.add_argument("--camera-id", default="north-entry")
    parser.add_argument("--camera-name", default="North entry")
    parser.add_argument("--location", default="Unspecified")
    parser.add_argument("--zone-id", default="entry")
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--confidence", type=float, default=0.35)
    parser.add_argument("--device", default=None, help="Inference device, e.g. cpu or cuda:0")
    parser.add_argument("--publish-every", type=int, default=5, help="Publish telemetry every N processed frames")
    parser.add_argument("--stream-every", type=int, default=1, help="Publish annotated video every N processed frames")
    parser.add_argument("--heartbeat-seconds", type=int, default=5)
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--worker-id", default=None)
    parser.add_argument("--token", default=os.getenv("DMJ_VISION_WORKER_TOKEN"))
    args = parser.parse_args()

    if args.publish_every < 1 or args.stream_every < 1 or args.heartbeat_seconds < 1:
        raise SystemExit("publish, stream, and heartbeat intervals must be positive")

    worker_id = args.worker_id or f"worker-{args.camera_id}"
    detector = PersonDetector(DetectorConfig(model=args.model, confidence=args.confidence, device=args.device))
    tracker = IoUTracker()

    heartbeat = threading.Thread(target=_heartbeat_loop, args=(args.api_url, args.camera_id, worker_id, args.camera_name, args.location, args.token, args.heartbeat_seconds), daemon=True)
    heartbeat.start()

    with VideoSource(args.source) as video:
        for frame in video.frames():
            detections = detector.detect(frame.image)
            tracks = tracker.update(detections)

            if frame.index % args.stream_every == 0:
                annotated = encode_annotated_frame(frame.image, tracks)
                try:
                    _request(args.api_url, f"/api/workers/{urllib.parse.quote(args.camera_id, safe='')}/frame", annotated, "image/jpeg", args.token)
                except Exception as exc:
                    print(f"frame publish error: {exc}")

            if frame.index % args.publish_every != 0:
                continue

            for track in tracks:
                if track.missed_frames:
                    continue
                observation = {
                    "camera_id": args.camera_id,
                    "zone_id": args.zone_id,
                    "observed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(frame.timestamp)),
                    "confidence": track.confidence,
                    "quality": 1.0,
                }
                query = urllib.parse.urlencode({"track_id": track.id})
                try:
                    result = _request(args.api_url, f"/api/observations?{query}", json.dumps(observation).encode(), "application/json", args.token)
                    print(f"{track.id} | {result.decode(errors='replace')[:120]}")
                except Exception as exc:
                    print(f"telemetry error for {track.id}: {exc}")


if __name__ == "__main__":
    main()
