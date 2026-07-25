import unittest
from app import app
from storage.db import get_connection


class MyDoctorsRouteTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def tearDown(self):
        for email in ["patient-my-doctors@example.com", "doctor-my-doctors@example.com"]:
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM appointments WHERE patient_id = ? OR doctor_id = ?", (email, email))
            cursor.execute("DELETE FROM patient_assignments WHERE patient_id = ? OR doctor_id = ?", (email, email))
            cursor.execute("DELETE FROM assignment_history WHERE patient_id = ? OR doctor_id = ?", (email, email))
            cursor.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
            conn.close()

    def test_my_doctors_page_renders_assigned_doctor_name(self):
        patient_email = "patient-my-doctors@example.com"
        doctor_email = "doctor-my-doctors@example.com"

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)", (patient_email, "hash", "patient", "Jane Doe"))
        cursor.execute("INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)", (doctor_email, "hash", "doctor", "Dr. Maya Chen"))
        cursor.execute("INSERT INTO patient_assignments (patient_id, doctor_id) VALUES (?, ?)", (patient_email, doctor_email))
        cursor.execute("INSERT INTO assignment_history (patient_id, doctor_id, assigned_at, unassigned_at) VALUES (?, ?, ?, ?)", (patient_email, doctor_email, "2026-07-25T10:00:00", None))
        cursor.execute("INSERT INTO appointments (appointment_id, patient_id, doctor_id, slot, status, created_at) VALUES (?, ?, ?, ?, ?, ?)", ("appt-1", patient_email, doctor_email, "2026-07-26 10:00:00", "scheduled", "2026-07-25T09:00:00"))
        conn.commit()
        conn.close()

        with self.client.session_transaction() as sess:
            sess["email"] = patient_email
            sess["role"] = "patient"
            sess["name"] = "Jane Doe"

        response = self.client.get("/patient/my-doctors")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Dr. Maya Chen", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()
