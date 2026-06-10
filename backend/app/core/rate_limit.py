"""Small in-process rate limiter for authentication endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_events: dict[str, deque[float]] = defaultdict(deque)
_lock = asyncio.Lock()
_MAX_KEYS = 10_000


async def enforce_rate_limit(
    request: Request,
    *,
    action: str,
    identifier: str = "",
    limit: int,
    window_seconds: int,
) -> None:
    """Reject repeated authentication requests within a fixed rolling window."""
    client_ip = request.client.host if request.client else "unknown"
    identity_hash = hashlib.sha256(identifier.strip().lower().encode()).hexdigest()[:16]
    key = f"{action}:{client_ip}:{identity_hash}"
    now = time.monotonic()
    cutoff = now - window_seconds

    async with _lock:
        if len(_events) >= _MAX_KEYS:
            expired_keys = [
                event_key
                for event_key, timestamps in _events.items()
                if not timestamps or timestamps[-1] <= cutoff
            ]
            for event_key in expired_keys:
                _events.pop(event_key, None)
            if len(_events) >= _MAX_KEYS and key not in _events:
                raise HTTPException(
                    status_code=429,
                    detail="Authentication rate limiter is at capacity. Please try again later.",
                    headers={"Retry-After": str(window_seconds)},
                )

        events = _events[key]
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(window_seconds)},
            )
        events.append(now)
