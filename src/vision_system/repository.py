from __future__ import annotations

from collections import Counter
from datetime import timedelta
from threading import Lock
from uuid import uuid4

from .models import AuditEvent, Camera, ContinuityCandidate, Observation, Track, TrackState, TrackSummary, utc_now


class VisionRepository:
    """Thread-safe demonstration repository; replace with durable storage in production."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.cameras = {
            "north-entry": Camera(id="north-entry", name="North entry", location="Level 1 · North"),
            "atrium": Camera(id="atrium", name="Atrium", location="Level 1 · Central"),
            "south-exit": Camera(id="south-exit", name="South exit", location="Level 1 · South"),
        }
        self.tracks: dict[str, Track] = {}
        # The Continuity Mesh only permits handoffs along explicitly configured routes.
        # Values are expected travel windows in seconds: (minimum, maximum).
        self.topology = {
            ("north-entry", "atrium"): (20, 360),
            ("atrium", "south-exit"): (20, 480),
        }
        self.audit_events: list[AuditEvent] = []
        self._seed_demo_data()

    def _seed_demo_data(self) -> None:
        now = utc_now()
        first = Track(id="trk_7f2a", state=TrackState.active, created_at=now - timedelta(minutes=8), last_seen_at=now)
        first.observations = [
            Observation(camera_id="north-entry", zone_id="entry", observed_at=now - timedelta(minutes=8), confidence=.93, direction="in", quality=.86),
            Observation(camera_id="atrium", zone_id="central-walkway", observed_at=now - timedelta(minutes=4), confidence=.88, direction="south", quality=.78),
        ]
        second = Track(id="trk_c91d", state=TrackState.lost, created_at=now - timedelta(minutes=12), last_seen_at=now - timedelta(minutes=2))
        second.observations = [
            Observation(camera_id="north-entry", zone_id="entry", observed_at=now - timedelta(minutes=12), confidence=.90, direction="in", quality=.72),
            Observation(camera_id="atrium", zone_id="central-walkway", observed_at=now - timedelta(minutes=2), confidence=.64, direction="east", quality=.45),
        ]
        handoff = Track(id="trk_ae10", state=TrackState.lost, created_at=now - timedelta(minutes=5), last_seen_at=now - timedelta(minutes=5))
        handoff.observations = [
            Observation(camera_id="north-entry", zone_id="entry", observed_at=now - timedelta(minutes=5), confidence=.89, direction="in", quality=.82),
        ]
        third = Track(id="trk_3b18", state=TrackState.exited, created_at=now - timedelta(minutes=20), last_seen_at=now - timedelta(minutes=1))
        third.observations = [
            Observation(camera_id="atrium", zone_id="central-walkway", observed_at=now - timedelta(minutes=20), confidence=.82, direction="south", quality=.75),
            Observation(camera_id="south-exit", zone_id="exit", observed_at=now - timedelta(minutes=1), confidence=.91, direction="out", quality=.88),
        ]
        self.tracks = {track.id: track for track in (first, second, handoff, third)}

    def list_tracks(self, state: TrackState | None = None) -> list[TrackSummary]:
        with self._lock:
            tracks = self.tracks.values()
            if state:
                tracks = (track for track in tracks if track.state == state)
            return sorted((self._summary(track) for track in tracks), key=lambda track: track.last_seen_at, reverse=True)

    def get_track(self, track_id: str, actor: str | None = None) -> Track | None:
        with self._lock:
            track = self.tracks.get(track_id)
            if track and actor:
                self.audit_events.append(AuditEvent(action="view_track", actor=actor, track_id=track_id))
            return track


    def continuity_candidates(self, track_id: str, actor: str | None = None) -> list[ContinuityCandidate] | None:
        """Return predecessor handoff propositions for a track.

        DMJ Continuity Mesh uses only configured camera topology, elapsed travel time,
        direction agreement, and existing observation quality/confidence. It never
        treats a result as an identity match.
        """
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
                route_window = self.topology.get((source_observation.camera_id, target_observation.camera_id))
                if route_window is None:
                    continue
                elapsed = int((target_observation.observed_at - source_observation.observed_at).total_seconds())
                minimum, maximum = route_window
                if elapsed < minimum or elapsed > maximum:
                    continue
                midpoint = (minimum + maximum) / 2
                half_window = max((maximum - minimum) / 2, 1)
                time_score = max(0.0, 1 - abs(elapsed - midpoint) / half_window)
                quality_score = (source_observation.quality + target_observation.quality) / 2
                detection_score = (source_observation.confidence + target_observation.confidence) / 2
                direction_score = 1.0 if source_observation.direction in {"in", "south", "east"} else 0.5
                score = round(0.35 + 0.25 * time_score + 0.2 * quality_score + 0.15 * detection_score + 0.05 * direction_score, 2)
                tier = "review" if score >= .8 else "possible" if score >= .65 else "weak"
                candidates.append(ContinuityCandidate(
                    track_id=source.id, score=score, tier=tier,
                    route=f"{source_observation.camera_id} → {target_observation.camera_id}",
                    elapsed_seconds=elapsed,
                    evidence=[
                        "configured camera route",
                        f"travel time {elapsed}s within {minimum}–{maximum}s window",
                        f"observation quality {round(quality_score * 100)}%",
                        f"detection confidence {round(detection_score * 100)}%",
                    ],
                ))
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
        with self._lock:
            states = Counter(track.state.value for track in self.tracks.values())
            zones = Counter(
                track.last_observation.zone_id for track in self.tracks.values()
                if track.state == TrackState.active and track.last_observation
            )
            return {
                "active_tracks": states["active"],
                "lost_tracks": states["lost"],
                "exited_tracks": states["exited"],
                "zone_occupancy": zones,
                "camera_count": len(self.cameras),
            }

    def _summary(self, track: Track) -> TrackSummary:
        last = track.last_observation
        return TrackSummary(
            id=track.id, state=track.state, last_seen_at=track.last_seen_at,
            current_camera_id=last.camera_id if last else None,
            current_zone_id=last.zone_id if last else None,
            confidence=last.confidence if last else 0, observation_count=len(track.observations),
        )
