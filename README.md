# DMJ Vision

A runnable MVP for an **authorized-site, privacy-aware vision operations console**. It demonstrates pseudonymous people tracks, camera/zone paths, counting-oriented status, confidence display, and operator-audited timeline access.

> This project does not perform face recognition, make identity claims, or store biometric templates. A track is a temporary, pseudonymous operational identifier. Production deployments need an explicit lawful purpose, role-based access, audit review, retention/deletion controls, and security review.

## Included MVP capabilities

- Live operations dashboard with active/lost/exited track counts.
- **Live annotated camera feed:** bounding boxes and pseudonymous track IDs are rendered from the worker and exposed as MJPEG.
- Site map showing movement context (camera, zone, direction, and confidence).
- Clickable track directory with last-known location and observation timeline.
- FastAPI endpoints for camera workers to create tracks and append observations.
- Confidence and image-quality fields so uncertain matches are never presented as certain.
- Header-based demonstration audit hook for timeline access.
- **DMJ Continuity Mesh (DCM):** topology-aware handoff propositions that combine route, time, direction, quality, and detector confidence without biometric matching.
- Seeded sample data for an immediate working demonstration.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,vision]'
uvicorn vision_system.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). The dashboard now contains the live **North entry** camera panel. Interactive API documentation is available at `/docs`.

Run a webcam worker in another terminal:

```bash
dmj-vision-worker --source 0 --camera-id north-entry --zone-id entry
```

The same command accepts a video file or RTSP URL:

```bash
dmj-vision-worker --source ./sample.mp4 --camera-id north-entry --zone-id entry
dmj-vision-worker --source 'rtsp://user:password@camera/stream' --camera-id north-entry --zone-id entry
```

Use `--device cuda:0` for an NVIDIA CUDA-enabled Ultralytics installation. `--publish-every 5` controls how often structured telemetry is sent to the API; visual frames continue to update continuously.

The worker sends annotated JPEG frames to the in-process stream hub and structured observations to FastAPI. The API never needs the raw video frame for track history.

## Camera stream API

```text
GET /api/cameras/{camera_id}/stream
```

The endpoint returns an MJPEG stream. The dashboard uses the North entry stream automatically. A production deployment should put the stream behind authentication and replace the in-process hub with a broker/shared stream layer when workers run on separate machines.

## API workflow

A camera worker can preserve its local pseudonymous track ID:

```bash
curl -X POST 'http://127.0.0.1:8000/api/observations?track_id=trk_worker1' \
  -H 'Content-Type: application/json' \
  -d '{"camera_id":"atrium","zone_id":"central-walkway","confidence":0.81,"quality":0.70,"direction":"south"}'
```

### Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Service health check. |
| `GET /api/overview` | Counts and live zone occupancy. |
| `GET /api/cameras` | Registered cameras. |
| `GET /api/cameras/{camera_id}/stream` | Live annotated MJPEG camera stream. |
| `GET /api/tracks` | Recent track summaries; supports `?state=active`. |
| `GET /api/tracks/{id}` | Full observation history; supports `X-Operator` audit attribution. |
| `GET /api/tracks/{id}/continuity-candidates` | Explainable DCM predecessor handoff propositions. |
| `POST /api/observations?track_id=...` | Create or append a pseudonymous worker track. |
| `POST /api/tracks/{id}/observations` | Add a new observation to an existing track. |

## DMJ Continuity Mesh

**DMJ Continuity Mesh (DCM)** is an explicitly configured camera-topology graph that creates confidence-scored *handoff propositions* between anonymous tracks. It uses the physical route, bounded travel-time window, direction, observation quality, and detection confidence. A proposition is never an identity claim. Read the complete architecture vocabulary, formula, and safeguards in [`docs/dmj-continuity-mesh.md`](docs/dmj-continuity-mesh.md).

## Production roadmap

1. **Camera workers:** add RTSP/ONVIF camera management, worker health reporting, configurable zones, and shared stream transport.
2. **Persistence:** replace the in-memory repository with PostgreSQL/TimescaleDB and encrypted object storage; implement retention jobs.
3. **Tracking:** evaluate a stronger production MOT backend and benchmark ID switches, missed detections, and latency on authorized site footage.
4. **Multi-camera association:** use camera topology, travel-time limits, direction, and bounded appearance signals. Display candidates and confidence—not identification claims.
5. **Operations hardening:** add OIDC/SSO, RBAC, immutable audits, encryption, model versioning, metrics, alerting, and load tests.
6. **Governance:** conduct a DPIA/privacy review, define access roles and retention periods, validate false-association performance in the actual installation, and document a human-review process.

## Development

```bash
pytest -q
```

The storage adapter remains isolated in `src/vision_system/repository.py`, while camera/video handling is isolated under `src/vision_system/vision/` and live-frame transport under `src/vision_system/stream.py`.
