from __future__ import annotations

from fastapi import Header, HTTPException

from .config import settings


def require_worker_token(authorization: str | None = Header(default=None)) -> None:
    if settings.mode != "live":
        return
    expected = f"Bearer {settings.worker_token}"
    if authorization != expected:
        raise HTTPException(status_code=401, detail="Invalid worker credentials")
