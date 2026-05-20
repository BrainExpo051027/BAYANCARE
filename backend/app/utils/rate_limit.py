"""Simple in-memory rate limiting keyed by IP and optional user id."""

from collections import defaultdict
from functools import wraps
from threading import Lock
from time import time

from flask import jsonify, request
from flask_login import current_user

_buckets: dict[str, list[float]] = defaultdict(list)
_lock = Lock()


def _rate_limit_key(suffix: str) -> str:
    return f"{request.remote_addr or 'unknown'}:{suffix}"


def _is_over_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    now = time()
    cutoff = now - window_seconds
    with _lock:
        timestamps = _buckets[key]
        _buckets[key] = [t for t in timestamps if t > cutoff]
        if len(_buckets[key]) >= max_requests:
            return True
        _buckets[key].append(now)
    return False


def rate_limit(max_requests=10, window_seconds=3600, per_user_limit=5):
    """
    Limit requests per IP and per authenticated user (when per_user_limit is set).
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if _is_over_limit(_rate_limit_key("ip"), max_requests, window_seconds):
                return jsonify({"success": False, "message": "Too many requests. Please try again later."}), 429

            if per_user_limit is not None and current_user.is_authenticated:
                user_key = _rate_limit_key(f"user:{current_user.id}")
                if _is_over_limit(user_key, per_user_limit, window_seconds):
                    return jsonify({"success": False, "message": "Too many requests. Please try again later."}), 429

            return f(*args, **kwargs)

        return wrapped

    return decorator
