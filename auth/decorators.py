from functools import wraps
from flask import session, jsonify


def require_role(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "role" not in session:
                return jsonify({"error": "Not logged in"}), 401
            if session["role"] != role:
                return jsonify({"error": f"This action requires the '{role}' role"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator