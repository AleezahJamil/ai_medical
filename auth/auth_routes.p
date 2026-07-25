from flask import Blueprint, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash
from storage.db import get_connection
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import secrets

auth_bp = Blueprint("auth", __name__)

GOOGLE_CLIENT_ID = "584375047286-36q6aut47qbuu07hc4f7bh1gr6grl5vb.apps.googleusercontent.com"


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

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        return jsonify({"error": "An account with this email already exists"}), 409

    password_hash = generate_password_hash(password)
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
        (email, password_hash, role, name),
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "account created", "email": email, "role": role})


@auth_bp.route("/auth/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    session["email"] = email
    session["role"] = user["role"]
    session["name"] = user["name"]

    return jsonify({"status": "logged in", "role": user["role"], "name": user["name"]})


@auth_bp.route("/auth/google", methods=["POST"])
def google_login():
    data = request.json
    credential = data.get("credential")
    role = data.get("role", "patient")

    if not credential:
        return jsonify({"error": "credential is required"}), 400

    try:
        idinfo = id_token.verify_oauth2_token(
            credential, google_requests.Request(), GOOGLE_CLIENT_ID
        )
    except ValueError:
        return jsonify({"error": "Invalid Google credential"}), 401

    email = idinfo["email"]
    name = idinfo.get("name", email)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()

    if not user:
        random_password_hash = generate_password_hash(secrets.token_hex(32))
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
            (email, random_password_hash, role, name),
        )
        conn.commit()
        user_role, user_name = role, name
    else:
        user_role, user_name = user["role"], user["name"]

    conn.close()

    session["email"] = email
    session["role"] = user_role
    session["name"] = user_name

    return jsonify({"status": "logged in", "email": email, "role": user_role, "name": user_name})


@auth_bp.route("/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"status": "logged out"})


@auth_bp.route("/auth/whoami", methods=["GET"])
def whoami():
    if "email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    return jsonify({
        "email": session["email"],
        "role": session["role"],
        "name": session["name"],
    })