from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from storage.db import get_connection

auth_bp = Blueprint("auth", __name__)

# TEMPORARY in-memory cache only; the database is the source of truth for user data.
users = {}  # email -> {"password_hash": ..., "role": "patient"/"doctor", "name": ...}


def get_user_from_db(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, password_hash, role, name, dob, phone FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user_to_db(email, password_hash, role, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
        (email, password_hash, role, name),
    )
    conn.commit()
    conn.close()


def update_user_profile(current_email, name, phone, dob, new_email=None):
    conn = get_connection()
    cursor = conn.cursor()

    if new_email and new_email != current_email:
        if get_user_from_db(new_email) is not None:
            conn.close()
            return {"error": "An account with this email already exists"}, 409

    final_email = new_email if new_email and new_email != current_email else current_email
    cursor.execute(
        "UPDATE users SET email = ?, name = ?, phone = ?, dob = ? WHERE email = ?",
        (final_email, name, phone or "", dob or "", current_email),
    )

    if new_email and new_email != current_email:
        cursor.execute("UPDATE summaries SET patient_id = ? WHERE patient_id = ?", (final_email, current_email))
        cursor.execute("UPDATE documents SET patient_id = ? WHERE patient_id = ?", (final_email, current_email))
        cursor.execute("UPDATE appointments SET patient_id = ? WHERE patient_id = ?", (final_email, current_email))
        cursor.execute("UPDATE patient_assignments SET patient_id = ? WHERE patient_id = ?", (final_email, current_email))
        cursor.execute("UPDATE assignment_history SET patient_id = ? WHERE patient_id = ?", (final_email, current_email))
        cursor.execute("UPDATE clinical_notes SET patient_id = ? WHERE patient_id = ?", (final_email, current_email))

    conn.commit()
    conn.close()

    if current_email in users:
        users[final_email] = users.pop(current_email)
        users[final_email]["name"] = name

    return {
        "email": final_email,
        "name": name,
        "phone": phone or "",
        "dob": dob or "",
    }


@auth_bp.route("/auth/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")
    name = data.get("name")

    if not all([email, password, role, name]):
        return jsonify({"error": "email, password, role, and name are required"}), 400

    if role not in ("patient", "doctor"):
        return jsonify({"error": "role must be 'patient' or 'doctor'"}), 400

    if get_user_from_db(email) is not None:
        return jsonify({"error": "An account with this email already exists"}), 409

    password_hash = generate_password_hash(password)
    save_user_to_db(email, password_hash, role, name)

    session["email"] = email
    session["role"] = role
    session["name"] = name

    return jsonify({"status": "account created", "email": email, "role": role})


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = get_user_from_db(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["email"] = email
    session["role"] = user["role"]
    session["name"] = user["name"]

    return jsonify({"status": "logged in", "role": user["role"], "name": user["name"]})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"})


@auth_bp.route("/auth/change-password", methods=["POST"])
def change_password():
    if "email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    data = request.json or {}
    current_password = data.get("current_password")
    new_password = data.get("new_password")
    if not current_password or not new_password:
        return jsonify({"error": "current_password and new_password are required"}), 400

    user = get_user_from_db(session["email"])
    if not user or not check_password_hash(user["password_hash"], current_password):
        return jsonify({"error": "Current password is incorrect"}), 403

    password_hash = generate_password_hash(new_password)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, session["email"]))
    conn.commit()
    conn.close()

    return jsonify({"status": "password changed"})


@auth_bp.route("/auth/whoami", methods=["GET"])
def whoami():
    if "email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "email": session["email"],
        "role": session["role"],
        "name": session["name"],
    })