"""
Notification routes for testing email functionality (admin-only, rate-limited).
"""

import re

from flask import Blueprint, current_app, jsonify, request
from app.utils.decorators import admin_required
from app.utils.email_utils import send_email, send_welcome_email
from app.utils.rate_limit import rate_limit

notification_bp = Blueprint("notifications", __name__)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _test_routes_enabled():
    return current_app.config.get("ENABLE_NOTIFICATION_TEST_ROUTES", False)


def _require_test_routes(f):
    """Return 404 when notification test routes are disabled (e.g. production)."""

    from functools import wraps

    @wraps(f)
    def wrapped(*args, **kwargs):
        if not _test_routes_enabled():
            return ("", 404)
        return f(*args, **kwargs)

    return wrapped


def _is_allowed_recipient(email: str) -> bool:
    if not email or not _EMAIL_RE.match(email):
        return False
    domain = email.rsplit("@", 1)[1].lower()
    allowed = current_app.config.get("ALLOWED_TEST_EMAIL_DOMAINS") or []
    return domain in allowed


def _generic_error_response(log_message: str = "Notification route error"):
    current_app.logger.exception(log_message)
    return jsonify({"success": False, "message": "An error occurred processing the request"}), 500


@notification_bp.route("/test-email", methods=["POST"])
@_require_test_routes
@admin_required
@rate_limit(max_requests=10, window_seconds=3600, per_user_limit=5)
def test_email():
    """Send a test email (admin only)."""
    try:
        data = request.get_json(silent=True) or {}
        recipient = (data.get("recipient") or "test@bayancare.local").strip()

        if not _is_allowed_recipient(recipient):
            return jsonify(
                {
                    "success": False,
                    "message": "Recipient email domain is not allowed for test sends",
                }
            ), 400

        subject = data.get("subject", "BAYANCARE Test Email")
        message = data.get(
            "message",
            "This is a test email from BAYANCARE notification system.",
        )

        success = send_email(recipient, subject, message)

        if success:
            return jsonify({"success": True, "message": "Test email sent successfully"})
        return jsonify({"success": False, "message": "Failed to send test email"}), 500

    except Exception:
        return _generic_error_response()


@notification_bp.route("/welcome-notification", methods=["POST"])
@_require_test_routes
@admin_required
@rate_limit(max_requests=10, window_seconds=3600, per_user_limit=5)
def welcome_notification():
    """Send welcome email (admin only)."""
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        name = data.get("name", "User")

        if not email:
            return jsonify({"success": False, "message": "Email address is required"}), 400

        if not _is_allowed_recipient(email):
            return jsonify(
                {
                    "success": False,
                    "message": "Recipient email domain is not allowed for test sends",
                }
            ), 400

        email_success = send_welcome_email(email, name)

        return jsonify(
            {
                "success": email_success,
                "message": "Welcome notification processed"
                if email_success
                else "Failed to send welcome notification",
            }
        )

    except Exception:
        return _generic_error_response()


@notification_bp.route("/appointment-reminder", methods=["POST"])
@_require_test_routes
@admin_required
@rate_limit(max_requests=10, window_seconds=3600, per_user_limit=5)
def appointment_reminder():
    """Send appointment reminder email (admin only)."""
    try:
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip()
        name = data.get("name", "Patient")
        appointment_date = data.get("appointment_date", "Tomorrow")
        appointment_time = data.get("appointment_time", "10:00 AM")

        if not email:
            return jsonify({"success": False, "message": "Email address is required"}), 400

        if not _is_allowed_recipient(email):
            return jsonify(
                {
                    "success": False,
                    "message": "Recipient email domain is not allowed for test sends",
                }
            ), 400

        from app.utils.email_utils import send_appointment_reminder

        email_success = send_appointment_reminder(
            email, name, appointment_date, appointment_time
        )

        return jsonify(
            {
                "success": email_success,
                "message": "Appointment reminder processed"
                if email_success
                else "Failed to send appointment reminder",
            }
        )

    except Exception:
        return _generic_error_response()


@notification_bp.route("/status", methods=["GET"])
@admin_required
def notification_status():
    """Get notification system status (admin only)."""
    try:
        return jsonify(
            {
                "success": True,
                "email_configured": True,
                "sms_enabled": False,
                "test_routes_enabled": _test_routes_enabled(),
                "message": "Email notification system is operational (SMS removed)",
            }
        )
    except Exception:
        return _generic_error_response()
