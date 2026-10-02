from __future__ import annotations

from collections import Counter
from datetime import timedelta
from threading import Lock
from uuid import uuid4

from .config import settings
from .models import AuditEvent, Camera, CameraHeartbeat, ContinuityCandidate, Observation, Track, TrackState, TrackSummary, utc_now


class VisionRepository:
    """Thread-safe repository. Demo data exists only when explicitly running in demo mode."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.cameras: dict[str, Camera] = {}
        self.tracks: dict[str, Track] = {}
        self.topology = {
            ("north-entry", "atrium"): (20, 360, {"in", "south", "east"}, {"south", "east", "out"}),
            ("atrium", "south-exit"): (20, 480, {"south", "east"}, {"out"}),
        }
        self.audit_events: list[AuditEvent] = []
        if settings.mode == "demo":
            self._seed_demo_data()

    def _seed_demo_data(self) -> None:
        now = utc_now()
        for camera_id, name, location in (("north-entry", "North entry", "DEMO · Level 1 · North"), ("atrium", "Atrium", "DEMO · Level 1 · Central"), ("south-exit", "South exit", "DEMO · Level 1 · South")):
            self.cameras[camera_id] = Camera(id=camera_id, name=name, location=location, status="demo")
        first = Track(id="trk_7f2a", state=TrackState.active, created_at=now - timedelta(minutes=8), last_seen_at=now)
        first.observations = [Observation(camera_id="north-entry", zone_id="entry", observed_at=now - timedelta(minutes=8), confidence=.93, direction="in", quality=.86), Observation(camera_id="atrium", zone_id="central-walkway", observed_at=now - timedelta(minutes=4), confidence=.88, direction="south", quality=.78)]
        second = Track(id="trk_c91d", state=TrackState.lost, created_at=now - timedelta(minutes=12), last_seen_at=now - timedelta(minutes=2))
        second.observations = [Observation(camera_id="north-entry", zone_id="entry", observed_at=now - timedelta(minutes=12), confidence=.90, direction="in", quality=.72), Observation(camera_id="atrium", zone_id="central-walkway", observed_at=now - timedelta(minutes=2), confidence=.64, direction="east", quality=.45)]
        handoff = Track(id="trk_ae10", state=TrackState.lost, created_at=now - timedelta(minutes=5), last_seen_at=now - timedelta(minutes=5), observations=[Observation(camera_id="north-entry", zone_id="entry", observed_at=now - timedelta(minutes=5), confidence=.89, direction="in", quality=.82)])
        third = Track(id="trk_3b18", state=TrackState.exited, created_at=now - timedelta(minutes=20), last_seen_at=now - timedelta(minutes=1))
        third.observations = [Observation(camera_id="atrium", zone_id="central-walkway", observed_at=now - timedelta(minutes=20), confidence=.82, direction="south", quality=.75), Observation(camera_id="south-exit", zone_id="exit", observed_at=now - timedelta(minutes=1), confidence=.91, direction="out", quality=.88)]
        self.tracks = {track.id: track for track in (first, second, handoff, third)}

    def register_heartbeat(self, heartbeat: CameraHeartbeat, name: str, location: str) -> Camera:
        received_at = utc_now()
        with self._lock:
            camera = self.cameras.get(heartbeat.camera_id)
            if camera is None:
                camera = Camera(id=heartbeat.camera_id, name=name, location=location, status="online")
                self.cameras[camera.id] = camera
            camera.status = "online"
            camera.last_heartbeat_at = received_at
            camera.worker_id = heartbeat.worker_id
            return camera

    def mark_frame(self, camera_id: str, frame_at) -> None:
        with self._lock:
            camera = self.cameras.get(camera_id)
            if camera:
                camera.status = "online"
                camera.last_frame_at = frame_at

    def refresh_camera_status(self) -> None:
        cutoff = utc_now() - timedelta(seconds=settings.heartbeat_timeout_seconds)
        stale_track_cutoff = utc_now() - timedelta(seconds=settings.track_stale_seconds)
        with self._lock:
            for camera in self.cameras.values():
                if camera.status != "demo" and (camera.last_heartbeat_at is None or camera.last_heartbeat_at < cutoff):
                    camera.status = "offline"
            for track in self.tracks.values():
                if track.state == TrackState.active and track.last_seen_at < stale_track_cutoff:
                    track.state = TrackState.lost

    def list_tracks(self, state: TrackState | None = None) -> list[TrackSummary]:
        self.refresh_camera_status()
        with self._lock:
            tracks = self.tracks.values()
            if state:
                tracks = (track for track in tracks if track.state == state)
            return sorted((self._summary(track) for track in tracks), key=lambda track: track.last_seen_at, reverse=True)

    def get_track(self, track_id: str, actor: str | None = None) -> Track | None:
        self.refresh_camera_status()
        with self._lock:
            track = self.tracks.get(track_id)
            if track and actor:
                self.audit_events.append(AuditEvent(action="view_track", actor=actor, track_id=track_id))
            return track

    def continuity_candidates(self, track_id: str, actor: str | None = None) -> list[ContinuityCandidate] | None:
        self.refresh_camera_status()
        with self._lock:
            target = self.tracks.get(track_id)
            if target is None or target.last_observation is None:
                return None
            if actor:
                self.audit_events.append(AuditEvent(action="view_continuity_candidates", actor=actor, track_id=track_id))
            target_observation = target.last_observation
            candidates: list[ContinuityCandidate] = []
            for source in self.tracks.values():
                if source.id == target.id or source.last_observation is None:
                    continue
                source_observation = source.last_observation
                topology = self.topology.get((source_observation.camera_id, target_observation.camera_id))
                if topology is None:
                    continue
                minimum, maximum, source_directions, target_directions = topology
                elapsed = int((target_observation.observed_at - source_observation.observed_at).total_seconds())
                if elapsed < minimum or elapsed > maximum:
                    continue
                midpoint = (minimum + maximum) / 2
                half_window = max((maximum - minimum) / 2, 1)
                time_score = max(0.0, 1 - abs(elapsed - midpoint) / half_window)
                quality_score = (source_observation.quality + target_observation.quality) / 2
                detection_score = (source_observation.confidence + target_observation.confidence) / 2
                direction_score = 1.0 if source_observation.direction in source_directions and target_observation.direction in target_directions else 0.0
                score = round(0.35 + 0.25 * time_score + 0.2 * quality_score + 0.15 * detection_score + 0.05 * direction_score, 2)
                tier = "review" if score >= .8 else "possible" if score >= .65 else "weak"
                candidates.append(ContinuityCandidate(track_id=source.id, score=score, tier=tier, route=f"{source_observation.camera_id} → {target_observation.camera_id}", elapsed_seconds=elapsed, evidence=["configured camera route", f"travel time {elapsed}s within {minimum}–{maximum}s window", f"observation quality {round(quality_score * 100)}%", f"detection confidence {round(detection_score * 100)}%", f"direction compatibility {round(direction_score * 100)}%"]))
            return sorted(candidates, key=lambda candidate: candidate.score, reverse=True)

    def create_observation(self, observation: Observation, track_id: str | None = None) -> Track:
        with self._lock:
            if observation.camera_id not in self.cameras:
                raise KeyError(observation.camera_id)
            if track_id and track_id in self.tracks:
                track = self.tracks[track_id]
                track.observations.append(observation)
                track.last_seen_at = observation.observed_at
                track.state = TrackState.active
                return track
            identifier = track_id or f"trk_{uuid4().hex[:8]}"
            track = Track(id=identifier, state=TrackState.active, created_at=observation.observed_at, last_seen_at=observation.observed_at, observations=[observation])
            self.tracks[identifier] = track
            return track

    def overview(self) -> dict:
        self.refresh_camera_status()
        with self._lock:
            states = Counter(track.state.value for track in self.tracks.values())
            zones = Counter(track.last_observation.zone_id for track in self.tracks.values() if track.state == TrackState.active and track.last_observation)
            online = sum(camera.status == "online" for camera in self.cameras.values())
            return {"mode": settings.mode, "active_tracks": states["active"], "lost_tracks": states["lost"], "exited_tracks": states["exited"], "zone_occupancy": zones, "camera_count": len(self.cameras), "online_camera_count": online}

    def _summary(self, track: Track) -> TrackSummary:
        last = track.last_observation
        return TrackSummary(id=track.id, state=track.state, last_seen_at=track.last_seen_at, current_camera_id=last.camera_id if last else None, current_zone_id=last.zone_id if last else None, confidence=last.confidence if last else 0, observation_count=len(track.observations))
