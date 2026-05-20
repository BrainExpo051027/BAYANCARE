from functools import wraps
from flask import jsonify
from flask_login import login_required, current_user
from app.models.user import Role


def admin_required(f):
    """Require an authenticated admin user."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != Role.ADMIN:
            return jsonify({"success": False, "message": "Admin access required"}), 403
        return f(*args, **kwargs)

    return decorated_function


def role_required(*allowed_roles):
    """
    Decorator to require specific roles to access an endpoint.
    Usage: @role_required(Role.BHW)
    """
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            if current_user.role not in allowed_roles:
                return jsonify({"error": "Insufficient permissions"}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator
