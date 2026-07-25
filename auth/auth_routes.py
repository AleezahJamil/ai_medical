import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from flask import Blueprint, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from storage.db import get_connection
from mailer.email_sender import send_verification_email, EmailSendError

auth_bp = Blueprint("auth", __name__)

# TEMPORARY in-memory cache only; the database is the source of truth for user data.
users = {}  # email -> {"password_hash": ..., "role": "patient"/"doctor", "name": ...}

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VERIFICATION_TOKEN_TTL = timedelta(hours=24)
RESEND_COOLDOWN = timedelta(seconds=60)


def _is_valid_email(email):
    return bool(email) and bool(_EMAIL_RE.match(email))


def _now():
    return datetime.now(timezone.utc)


def _generate_verification_token():
    """Return (raw_token, token_hash). Only token_hash is ever stored."""
    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash


def _build_verify_url(raw_token):
    base = os.getenv("APP_BASE_URL")
    if base:
        return base.rstrip("/") + url_for("auth.verify_email", token=raw_token)
    return url_for("auth.verify_email", token=raw_token, _external=True)


def get_user_from_db(email):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT email, password_hash, role, name, dob, phone, is_verified, "
        "verification_token_hash, verification_token_expires_at, verification_sent_at, "
        "doctor_status, doctor_specialty, doctor_hospital, doctor_license_number "
        "FROM users WHERE email = ?",
        (email,),
    )
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def save_user_to_db(email, password_hash, role, name, verification_token_hash, verification_token_expires_at,
                     doctor_status="approved"):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, name, is_verified, "
        "verification_token_hash, verification_token_expires_at, verification_sent_at, doctor_status) "
        "VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?)",
        (email, password_hash, role, name, verification_token_hash, verification_token_expires_at,
         _now().isoformat(), doctor_status),
    )
    conn.commit()
    conn.close()


def update_doctor_professional_info(doctor_id, specialty, hospital, license_number):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET doctor_specialty = ?, doctor_hospital = ?, doctor_license_number = ? WHERE email = ?",
        (specialty or "", hospital or "", license_number or "", doctor_id),
    )
    conn.commit()
    conn.close()


def update_doctor_status(doctor_id, new_status):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET doctor_status = ? WHERE email = ? AND role = 'doctor'", (new_status, doctor_id))
    updated = cursor.rowcount
    conn.commit()
    conn.close()
    return updated > 0


def get_doctors_by_status(status=None):
    conn = get_connection()
    cursor = conn.cursor()
    if status:
        cursor.execute(
            "SELECT email, name, phone, dob, doctor_status, doctor_specialty, doctor_hospital, "
            "doctor_license_number FROM users WHERE role = 'doctor' AND doctor_status = ? ORDER BY name",
            (status,),
        )
    else:
        cursor.execute(
            "SELECT email, name, phone, dob, doctor_status, doctor_specialty, doctor_hospital, "
            "doctor_license_number FROM users WHERE role = 'doctor' ORDER BY "
            "CASE doctor_status WHEN 'pending' THEN 0 ELSE 1 END, name"
        )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


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

    if not _is_valid_email(email):
        return jsonify({"error": "Please enter a valid email address"}), 400

    if get_user_from_db(email) is not None:
        return jsonify({"error": "An account with this email already exists"}), 409

    password_hash = generate_password_hash(password)
    raw_token, token_hash = _generate_verification_token()
    expires_at = (_now() + VERIFICATION_TOKEN_TTL).isoformat()
    doctor_status = "pending" if role == "doctor" else "approved"

    save_user_to_db(email, password_hash, role, name, token_hash, expires_at, doctor_status=doctor_status)

    verify_url = _build_verify_url(raw_token)
    try:
        send_verification_email(email, name, verify_url)
    except EmailSendError:
        return jsonify({
            "error": "We couldn't send your verification email right now. Please try again shortly.",
            "error_code": "email_send_failed",
        }), 503

    # No session is created here — the account cannot log in until it is verified.
    return jsonify({"status": "verification_sent", "email": email})


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = get_user_from_db(email)
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    if not user["is_verified"]:
        return jsonify({
            "error": "Please verify your email before logging in.",
            "error_code": "unverified",
        }), 403

    session["email"] = email
    session["role"] = user["role"]
    session["name"] = user["name"]

    return jsonify({"status": "logged in", "role": user["role"], "name": user["name"]})


@auth_bp.route("/auth/verify", methods=["GET"])
def verify_email():
    token = request.args.get("token", "")
    if not token:
        return redirect(url_for("login_page", verify_error="invalid"))

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT email, verification_token_expires_at FROM users "
        "WHERE verification_token_hash = ? AND is_verified = 0",
        (token_hash,),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return redirect(url_for("login_page", verify_error="invalid"))

    expires_at = row["verification_token_expires_at"]
    if not expires_at or datetime.fromisoformat(expires_at) < _now():
        conn.close()
        return redirect(url_for("login_page", verify_error="expired"))

    cursor.execute(
        "UPDATE users SET is_verified = 1, verification_token_hash = NULL, "
        "verification_token_expires_at = NULL, verification_sent_at = NULL WHERE email = ?",
        (row["email"],),
    )
    conn.commit()
    conn.close()

    return redirect(url_for("login_page", verified="1"))


@auth_bp.route("/auth/resend-verification", methods=["POST"])
def resend_verification():
    data = request.json or {}
    email = data.get("email")

    generic_message = (
        "If an account exists for that email and isn't yet verified, "
        "a new verification link has been sent."
    )

    if not email:
        return jsonify({"status": generic_message})

    user = get_user_from_db(email)
    if not user or user["is_verified"]:
        return jsonify({"status": generic_message})

    sent_at = user.get("verification_sent_at")
    if sent_at:
        try:
            if _now() - datetime.fromisoformat(sent_at) < RESEND_COOLDOWN:
                return jsonify({"status": generic_message})
        except ValueError:
            pass

    raw_token, token_hash = _generate_verification_token()
    expires_at = (_now() + VERIFICATION_TOKEN_TTL).isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET verification_token_hash = ?, verification_token_expires_at = ?, "
        "verification_sent_at = ? WHERE email = ?",
        (token_hash, expires_at, _now().isoformat(), email),
    )
    conn.commit()
    conn.close()

    verify_url = _build_verify_url(raw_token)
    try:
        send_verification_email(email, user["name"], verify_url)
    except EmailSendError:
        # Stay silent either way — never reveal whether the send succeeded.
        pass

    return jsonify({"status": generic_message})


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