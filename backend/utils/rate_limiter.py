"""
Lightweight in-memory sliding-window rate limiter for FastAPI.

Prevents DoS, abuse, and brute-force attacks on sensitive endpoints.
"""

import time
import threading
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException

_lock = threading.Lock()
# Mapping of key (ip_or_user:endpoint_tag) -> list of timestamp floats
_request_history: Dict[str, List[float]] = {}


def check_rate_limit(
    key: str,
    max_requests: int = 30,
    window_seconds: int = 60,
) -> Tuple[bool, int]:
    """
    Check if a key has exceeded max_requests in window_seconds.
    Returns (is_allowed: bool, retry_after_seconds: int).
    """
    now = time.time()
    cutoff = now - window_seconds

    with _lock:
        timestamps = _request_history.get(key, [])
        # Prune old timestamps
        valid_timestamps = [t for t in timestamps if t > cutoff]

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            _request_history[key] = valid_timestamps
            return False, retry_after

        valid_timestamps.append(now)
        _request_history[key] = valid_timestamps

        # Cleanup memory if dictionary grows very large
        if len(_request_history) > 10000:
            for k in list(_request_history.keys()):
                _request_history[k] = [t for t in _request_history[k] if t > cutoff]
                if not _request_history[k]:
                    del _request_history[k]

        return True, 0


async def rate_limit_auth(request: Request):
    """Rate limiter dependency for sensitive auth and tracking endpoints (15 req/min)."""
    client_ip = request.client.host if request.client else "unknown"
    key = f"{client_ip}:auth_sensitive"
    allowed, retry_after = check_rate_limit(key, max_requests=20, window_seconds=60)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

