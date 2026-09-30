from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.responses import FileResponse

from .models import Observation, Track, TrackState, TrackSummary
from .repository import VisionRepository

app = FastAPI(title="DMJ Vision", version="0.1.0", description="Privacy-aware vision operations API")
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
    return {"status": "ok", "service": "dmj-vision"}


@app.get("/api/overview")
def overview() -> dict:
    return repository.overview()


@app.get("/api/cameras")
def cameras() -> list:
    return list(repository.cameras.values())


@app.get("/api/tracks", response_model=list[TrackSummary])
def list_tracks(state: TrackState | None = None) -> list[TrackSummary]:
    return repository.list_tracks(state)


@app.get("/api/tracks/{track_id}", response_model=Track)
def get_track(track_id: str, x_operator: str | None = Header(default=None)) -> Track:
    track = repository.get_track(track_id, actor=x_operator)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@app.post("/api/tracks/{track_id}/observations", response_model=Track, status_code=201)
def add_observation(track_id: str, observation: Observation) -> Track:
    try:
        return repository.create_observation(observation, track_id)
    except KeyError:
        raise HTTPException(status_code=422, detail="Unknown camera_id") from None


@app.post("/api/observations", response_model=Track, status_code=201)
def create_track(observation: Observation, response: Response) -> Track:
    response.headers["Cache-Control"] = "no-store"
    return repository.create_observation(observation)
