from functools import wraps
from flask import session, jsonify
from auth.auth_routes import get_user_from_db


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


def require_approved_doctor(f):
    """Like require_role("doctor"), but also requires doctor_status == "approved".

    Looks the status up fresh from the database on every request rather than
    trusting anything cached in the session, so a doctor an admin suspends or
    rejects loses clinical access on their very next request, not just their
    next login.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "role" not in session:
            return jsonify({"error": "Not logged in"}), 401
        if session["role"] != "doctor":
            return jsonify({"error": "This action requires the 'doctor' role"}), 403

        user = get_user_from_db(session["email"])
        if not user or user.get("doctor_status") != "approved":
            return jsonify({
                "error": "Your doctor account is not yet approved for clinical access.",
                "error_code": "doctor_not_approved",
            }), 403
        return f(*args, **kwargs)
    return wrapper