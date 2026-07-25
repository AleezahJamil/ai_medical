import os
import unittest
from app import app
from storage.db import get_connection


class NameDisplayTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()
        # Signup now requires sending a real verification email; use the
        # explicit dev-mode fallback so this test doesn't need real email
        # provider credentials to exercise /auth/signup.
        self._prev_mail_dev_mode = os.environ.get("MAIL_DEV_MODE")
        os.environ["MAIL_DEV_MODE"] = "true"

    def tearDown(self):
        if self._prev_mail_dev_mode is None:
            os.environ.pop("MAIL_DEV_MODE", None)
        else:
            os.environ["MAIL_DEV_MODE"] = self._prev_mail_dev_mode
        self.cleanup_user("patient-name-test@example.com")
        self.cleanup_user("doctor-name-test@example.com")

    def cleanup_user(self, email):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM appointments WHERE patient_id = ? OR doctor_id = ?", (email, email))
        cursor.execute("DELETE FROM users WHERE email = ?", (email,))
        conn.commit()
        conn.close()

    def test_signup_persists_full_name_and_dashboard_uses_it(self):
        patient_email = "patient-name-test@example.com"
        doctor_email = "doctor-name-test@example.com"
        self.cleanup_user(patient_email)
        self.cleanup_user(doctor_email)

        signup_resp = self.client.post(
            "/auth/signup",
            json={
                "email": patient_email,
                "password": "secret123",
                "role": "patient",
                "name": "Ada Lovelace",
            },
        )
        self.assertEqual(signup_resp.status_code, 200)

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM users WHERE email = ?", (patient_email,))
        row = cursor.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row["name"], "Ada Lovelace")

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
            (doctor_email, "hash", "doctor", "Dr. Grace Hopper"),
        )
        cursor.execute(
            "INSERT INTO appointments (appointment_id, patient_id, doctor_id, slot, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            ("appt-test-1", patient_email, doctor_email, "2026-07-25 10:00:00", "scheduled", "2026-07-25T09:00:00"),
        )
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess["email"] = patient_email
            sess["role"] = "patient"
            sess["name"] = "Ada Lovelace"

        dashboard_resp = self.client.get("/patient/dashboard")
        self.assertEqual(dashboard_resp.status_code, 200)
        html = dashboard_resp.get_data(as_text=True)
        self.assertIn("Dr. Grace Hopper", html)
        self.assertNotIn(patient_email, html)


if __name__ == "__main__":
    unittest.main()
