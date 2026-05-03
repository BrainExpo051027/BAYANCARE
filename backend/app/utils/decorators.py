from functools import wraps
from flask import request, jsonify, current_app
from flask_login import login_required, current_user
from app.models.user import Role

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
