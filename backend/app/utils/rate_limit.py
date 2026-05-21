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


def _prune(key: str, window_seconds: int) -> int:
    now = time()
    cutoff = now - window_seconds
    with _lock:
        _buckets[key] = [t for t in _buckets[key] if t > cutoff]
        return len(_buckets[key])


def _at_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    return _prune(key, window_seconds) >= max_requests


def _record_hit(key: str) -> None:
    with _lock:
        _buckets[key].append(time())


def _is_over_limit(key: str, max_requests: int, window_seconds: int) -> bool:
    if _at_limit(key, max_requests, window_seconds):
        return True
    _record_hit(key)
    return False


def rate_limit_auth_register(f):
    """Limit public registration by IP and by email/username."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if _is_over_limit(_rate_limit_key("register:ip"), 10, 3600):
            return jsonify({"error": "Too many registration attempts. Please try again later."}), 429

        data = request.get_json(silent=True) or {}
        for field in ("email", "username"):
            ident = (data.get(field) or "").strip().lower()
            if ident and _is_over_limit(_rate_limit_key(f"register:{field}:{ident}"), 5, 3600):
                return jsonify({"error": "Too many registration attempts for this account. Please try again later."}), 429

        return f(*args, **kwargs)

    return wrapped


def check_login_rate_limits(username):
    """Return an error response tuple if login should be blocked, else None."""
    if _is_over_limit(_rate_limit_key("login:ip"), 30, 900):
        return jsonify({"error": "Too many login attempts. Please try again later."}), 429

    ident = (username or "").strip().lower()
    if ident and _is_over_limit(_rate_limit_key(f"login:user:{ident}"), 15, 900):
        return jsonify({"error": "Too many login attempts for this account. Please try again later."}), 429

    if ident and _at_limit(_rate_limit_key(f"login:fail:{ident}"), 5, 900):
        return jsonify({"error": "Too many failed login attempts. Please try again later."}), 429

    return None


def record_login_failure(username):
    ident = (username or "").strip().lower()
    if ident:
        key = _rate_limit_key(f"login:fail:{ident}")
        if not _at_limit(key, 5, 900):
            _record_hit(key)


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
