from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TrackState(str, Enum):
    active = "active"
    lost = "lost"
    exited = "exited"


class Observation(BaseModel):
    """A pseudonymous sighting emitted by a camera worker.

    This MVP deliberately stores no names, face templates, or identity claims.
    """

    camera_id: Annotated[str, Field(min_length=1, max_length=64)]
    zone_id: Annotated[str, Field(min_length=1, max_length=64)]
    observed_at: datetime = Field(default_factory=utc_now)
    confidence: Annotated[float, Field(ge=0, le=1)]
    direction: str | None = Field(default=None, max_length=32)
    quality: Annotated[float, Field(default=0.5, ge=0, le=1)]


class Track(BaseModel):
    id: str
    state: TrackState
    created_at: datetime
    last_seen_at: datetime
    observations: list[Observation] = Field(default_factory=list)

    @property
    def last_observation(self) -> Observation | None:
        return self.observations[-1] if self.observations else None


class TrackSummary(BaseModel):
    id: str
    state: TrackState
    last_seen_at: datetime
    current_camera_id: str | None
    current_zone_id: str | None
    confidence: float
    observation_count: int


class Camera(BaseModel):
    id: str
    name: str
    location: str
    status: str = "online"


class AuditEvent(BaseModel):
    action: str
    actor: str
    track_id: str | None = None
    occurred_at: datetime = Field(default_factory=utc_now)
