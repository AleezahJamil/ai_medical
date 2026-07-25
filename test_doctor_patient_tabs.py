import os
import json
from app import app
from storage.db import get_connection


def clear_patient_data(patient_id, doctor_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM summaries WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM intake_history WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM documents WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM clinical_notes WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM patient_assignments WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM assignment_history WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM appointments WHERE patient_id = ? AND doctor_id = ?", (patient_id, doctor_id))
    cur.execute("DELETE FROM users WHERE email IN (?, ?)", (patient_id, doctor_id))
    conn.commit()
    conn.close()


def test_doctor_patient_tabs_render_real_patient_data():
    patient_id = "patient-tabs@example.com"
    doctor_id = "doctor-tabs@example.com"
    clear_patient_data(patient_id, doctor_id)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
        (patient_id, "hash", "patient", "Patient Tabs"),
    )
    cur.execute(
        "INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)",
        (doctor_id, "hash", "doctor", "Dr. Tabs"),
    )
    cur.execute(
        "INSERT INTO patient_assignments (patient_id, doctor_id) VALUES (?, ?)",
        (patient_id, doctor_id),
    )
    cur.execute(
        "INSERT INTO summaries (patient_id, summary_json) VALUES (?, ?)",
        (patient_id, json.dumps({"main_concern": "Chest pressure", "symptoms": [{"label": "Chest pressure", "detail": "Intermittent", "flagged": True}]})),
    )
    cur.execute(
        "INSERT INTO intake_history (patient_id, concern, completed_at, status) VALUES (?, ?, ?, ?)",
        (patient_id, "Recent dizziness", "2026-07-20T10:00:00", "Reviewed"),
    )
    cur.execute(
        "INSERT INTO documents (patient_id, analysis_json) VALUES (?, ?)",
        (patient_id, json.dumps({"filename": "labs.txt", "summary": "CBC reviewed", "uploaded_at": "2026-07-21"})),
    )
    cur.execute(
        "INSERT INTO clinical_notes (patient_id, doctor_id, original_note, improved_note) VALUES (?, ?, ?, ?)",
        (patient_id, doctor_id, "Patient reports fatigue", "Patient reports fatigue."),
    )
    conn.commit()
    conn.close()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["email"] = doctor_id
        sess["role"] = "doctor"
        sess["name"] = "Dr. Tabs"

    overview_resp = client.get(f"/doctor/patient/{patient_id}")
    assert overview_resp.status_code == 200
    html = overview_resp.get_data(as_text=True)
    assert f"/doctor/patient/{patient_id}?tab=intake-history" in html
    assert f"/doctor/patient/{patient_id}?tab=clinical-summaries" in html
    assert f"/doctor/patient/{patient_id}?tab=documents" in html
    assert f"/doctor/patient/{patient_id}?tab=clinical-notes" in html

    intake_resp = client.get(f"/doctor/patient/{patient_id}?tab=intake-history")
    assert intake_resp.status_code == 200
    assert "Recent dizziness" in intake_resp.get_data(as_text=True)

    summary_resp = client.get(f"/doctor/patient/{patient_id}?tab=clinical-summaries")
    assert summary_resp.status_code == 200
    assert "Chest pressure" in summary_resp.get_data(as_text=True)

    docs_resp = client.get(f"/doctor/patient/{patient_id}?tab=documents")
    assert docs_resp.status_code == 200
    assert "labs.txt" in docs_resp.get_data(as_text=True)

    notes_resp = client.get(f"/doctor/patient/{patient_id}?tab=clinical-notes")
    assert notes_resp.status_code == 200
    assert "Patient reports fatigue" in notes_resp.get_data(as_text=True)
