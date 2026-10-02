from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse, StreamingResponse

from .config import settings
from .models import CameraHeartbeat, ContinuityCandidate, Observation, Track, TrackState, TrackSummary, utc_now
from .repository import VisionRepository
from .stream import mjpeg_stream, stream_hub
from .worker_auth import require_worker_token

app = FastAPI(title="DMJ Vision", version="0.3.0", description="Privacy-aware vision operations API")
repository = VisionRepository()
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/static/{asset_path:path}", include_in_schema=False)
def static_asset(asset_path: str) -> FileResponse:
    path = (STATIC_DIR / asset_path).resolve()
    if STATIC_DIR not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Asset not found")
    return FileResponse(path)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "dmj-vision", "mode": settings.mode}


@app.get("/api/overview")
def overview() -> dict:
    return repository.overview()


@app.get("/api/cameras")
def cameras() -> list:
    repository.refresh_camera_status()
    return list(repository.cameras.values())


@app.post("/api/workers/heartbeat")
def worker_heartbeat(heartbeat: CameraHeartbeat, name: str = Query(min_length=1, max_length=128), location: str = Query(min_length=1, max_length=256), authorization: str | None = Header(default=None)):
    require_worker_token(authorization)
    return repository.register_heartbeat(heartbeat, name=name, location=location)


@app.post("/api/workers/{camera_id}/frame")
async def worker_frame(camera_id: str, request: Request, authorization: str | None = Header(default=None)) -> dict[str, object]:
    require_worker_token(authorization)
    if camera_id not in repository.cameras:
        raise HTTPException(status_code=404, detail="Camera is not registered")
    body = await request.body()
    if len(body) > settings.max_frame_bytes:
        raise HTTPException(status_code=413, detail="Frame is too large")
    if not body.startswith(b"\xff\xd8"):
        raise HTTPException(status_code=415, detail="Expected JPEG frame")
    stream_hub.publish(camera_id, body)
    repository.mark_frame(camera_id, utc_now())
    return {"accepted": True, "camera_id": camera_id, "bytes": len(body)}


@app.get("/api/cameras/{camera_id}/stream")
def camera_stream(camera_id: str):
    if camera_id not in repository.cameras:
        raise HTTPException(status_code=404, detail="Camera not found")
    return StreamingResponse(mjpeg_stream(camera_id), media_type="multipart/x-mixed-replace; boundary=frame", headers={"Cache-Control": "no-cache"})


@app.get("/api/tracks", response_model=list[TrackSummary])
def list_tracks(state: TrackState | None = None) -> list[TrackSummary]:
    return repository.list_tracks(state)


@app.get("/api/tracks/{track_id}", response_model=Track)
def get_track(track_id: str, x_operator: str | None = Header(default=None)) -> Track:
    track = repository.get_track(track_id, actor=x_operator)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@app.get("/api/tracks/{track_id}/continuity-candidates", response_model=list[ContinuityCandidate])
def continuity_candidates(track_id: str, x_operator: str | None = Header(default=None)) -> list[ContinuityCandidate]:
    candidates = repository.continuity_candidates(track_id, actor=x_operator)
    if candidates is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return candidates


@app.post("/api/tracks/{track_id}/observations", response_model=Track, status_code=201)
def add_observation(track_id: str, observation: Observation, authorization: str | None = Header(default=None)) -> Track:
    require_worker_token(authorization)
    try:
        return repository.create_observation(observation, track_id)
    except KeyError:
        raise HTTPException(status_code=422, detail="Unknown camera_id") from None


@app.post("/api/observations", response_model=Track, status_code=201)
def create_track(observation: Observation, response: Response, track_id: str | None = Query(default=None, min_length=5, max_length=64), authorization: str | None = Header(default=None)) -> Track:
    require_worker_token(authorization)
    response.headers["Cache-Control"] = "no-store"
    try:
        return repository.create_observation(observation, track_id)
    except KeyError:
        raise HTTPException(status_code=422, detail="Unknown camera_id") from None
