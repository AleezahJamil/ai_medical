import pytest
from werkzeug.security import generate_password_hash

from app import app
from storage.db import get_connection


@pytest.fixture(autouse=True)
def clean_doctor_user():
    email = "doctor-profile-test@example.com"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    cursor.execute("DELETE FROM doctors WHERE doctor_id = ?", (email,))
    conn.commit()
    conn.close()

    yield

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE email = ?", (email,))
    cursor.execute("DELETE FROM doctors WHERE doctor_id = ?", (email,))
    conn.commit()
    conn.close()


def test_doctor_profile_and_settings_pages_render():
    email = "doctor-profile-test@example.com"
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, name, phone, dob) VALUES (?, ?, ?, ?, ?, ?)",
        (email, generate_password_hash("secret"), "doctor", "Dr. Test", "555-0100", "1985-02-01"),
    )
    conn.commit()
    conn.close()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["email"] = email
        sess["role"] = "doctor"
        sess["name"] = "Dr. Test"

    profile_response = client.get("/doctor/profile")
    assert profile_response.status_code == 200
    assert b"doctor profile" in profile_response.data.lower()
    assert b"/doctor/settings" in profile_response.data

    settings_response = client.get("/doctor/settings")
    assert settings_response.status_code == 200
    assert b"doctor settings" in settings_response.data.lower()
    assert b"/doctor/profile" in settings_response.data
