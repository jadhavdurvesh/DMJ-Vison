# DMJ Vision

A runnable MVP for an **authorized-site, privacy-aware vision operations console**. It demonstrates pseudonymous people tracks, camera/zone paths, counting-oriented status, confidence display, and operator-audited timeline access.

> This project does not perform face recognition, make identity claims, or store biometric templates. A track is a temporary, pseudonymous operational identifier. Production deployments need an explicit lawful purpose, role-based access, audit review, retention/deletion controls, and security review.

## Included MVP capabilities

- Live operations dashboard with active/lost/exited track counts.
- Site map showing low-resolution friendly movement context (camera, zone, direction, and confidence).
- Clickable track directory with last-known location and observation timeline.
- FastAPI endpoints for camera workers to create tracks and append observations.
- Confidence and image-quality fields so uncertain matches are never presented as certain.
- Header-based demonstration audit hook for timeline access.
- Seeded sample data for an immediate working demonstration.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn vision_system.main:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). Interactive API documentation is available at `/docs`.

Or run the container:

```bash
docker build -t dmj-vision .
docker run --rm -p 8000:8000 dmj-vision
```

## API workflow

A camera inference worker submits an observation, creating a new pseudonymous track:

```bash
curl -X POST http://127.0.0.1:8000/api/observations \
  -H 'Content-Type: application/json' \
  -d '{"camera_id":"atrium","zone_id":"central-walkway","confidence":0.81,"quality":0.70,"direction":"south"}'
```

A worker can append another sighting to the returned `id`:

```bash
curl -X POST http://127.0.0.1:8000/api/tracks/trk_example/observations \
  -H 'Content-Type: application/json' \
  -d '{"camera_id":"south-exit","zone_id":"exit","confidence":0.88,"quality":0.78,"direction":"out"}'
```

### Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/health` | Service health check. |
| `GET /api/overview` | Counts and live zone occupancy. |
| `GET /api/cameras` | Registered cameras. |
| `GET /api/tracks` | Recent track summaries; supports `?state=active`. |
| `GET /api/tracks/{id}` | Full observation history; supports `X-Operator` audit attribution. |
| `POST /api/observations` | Create a pseudonymous track from a camera observation. |
| `POST /api/tracks/{id}/observations` | Add a new observation to an existing track. |

## Production roadmap

1. **Camera workers:** replace seeded events with RTSP/ONVIF ingestion, low-resolution person detection, and a multi-object tracker.
2. **Persistence:** replace the in-memory repository with PostgreSQL/TimescaleDB and encrypted object storage; implement retention jobs.
3. **Multi-camera association:** use camera topology, travel-time limits, direction, and body-appearance signals. Display candidates and confidence—not identification claims.
4. **Operations hardening:** add OIDC/SSO, RBAC, immutable audits, encryption, model versioning, metrics, worker health checks, alerting, and load tests.
5. **Governance:** conduct a DPIA/privacy review, define access roles and retention periods, validate false-association performance in the actual installation, and document a human-review process.

## Development

```bash
pytest -q
```

The implementation intentionally keeps the storage adapter small and isolated in `src/vision_system/repository.py`, making it straightforward to replace with a durable database-backed implementation.
