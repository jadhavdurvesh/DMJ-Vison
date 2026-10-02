from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    mode: str = os.getenv("DMJ_VISION_MODE", "demo").strip().lower()
    worker_token: str | None = os.getenv("DMJ_VISION_WORKER_TOKEN") or None
    heartbeat_timeout_seconds: int = int(os.getenv("DMJ_VISION_HEARTBEAT_TIMEOUT", "15"))
    max_frame_bytes: int = int(os.getenv("DMJ_VISION_MAX_FRAME_BYTES", str(2 * 1024 * 1024)))

    def __post_init__(self) -> None:
        if self.mode not in {"demo", "live"}:
            raise ValueError("DMJ_VISION_MODE must be demo or live")
        if self.heartbeat_timeout_seconds < 1:
            raise ValueError("heartbeat timeout must be positive")
        if self.max_frame_bytes < 1024:
            raise ValueError("max frame size must be at least 1024")
        if self.mode == "live" and not self.worker_token:
            raise ValueError("worker token is required in live mode")


settings = Settings()
