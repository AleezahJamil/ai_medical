import json
from app import app
from storage.db import get_connection


def clear_test_data(patient_id, doctor_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM summaries WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM clinical_notes WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM patient_assignments WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM assignment_history WHERE patient_id = ?", (patient_id,))
    cur.execute("DELETE FROM appointments WHERE patient_id = ? AND doctor_id = ?", (patient_id, doctor_id))
    cur.execute("DELETE FROM users WHERE email IN (?, ?)", (patient_id, doctor_id))
    conn.commit()
    conn.close()


def test_doctor_can_save_summary_and_note():
    patient_id = "patient-docs@example.com"
    doctor_id = "doctor-docs@example.com"
    clear_test_data(patient_id, doctor_id)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)", (patient_id, "hash", "patient", "Doc Patient"))
    cur.execute("INSERT INTO users (email, password_hash, role, name) VALUES (?, ?, ?, ?)", (doctor_id, "hash", "doctor", "Dr. Docs"))
    cur.execute("INSERT INTO patient_assignments (patient_id, doctor_id) VALUES (?, ?)", (patient_id, doctor_id))
    cur.execute("INSERT INTO summaries (patient_id, summary_json) VALUES (?, ?)", (patient_id, json.dumps({"main_concern": "Initial AI summary", "symptoms": []})))
    conn.commit()
    conn.close()

    client = app.test_client()
    with client.session_transaction() as sess:
        sess["email"] = doctor_id
        sess["role"] = "doctor"
        sess["name"] = "Dr. Docs"

    save_summary_resp = client.post(
        f"/doctor/summary/{patient_id}/save",
        data={"summary_text": "Updated concern after review", "editor_name": "Dr. Docs"},
        follow_redirects=False,
    )
    assert save_summary_resp.status_code == 302

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT summary_json FROM summaries WHERE patient_id = ?", (patient_id,))
    summary_row = cur.fetchone()
    conn.close()
    summary = json.loads(summary_row["summary_json"])
    assert summary["main_concern"] == "Updated concern after review"

    save_note_resp = client.post(
        f"/doctor/notes/{patient_id}",
        data={"note_text": "Follow-up planned", "editor_name": "Dr. Docs"},
        follow_redirects=False,
    )
    assert save_note_resp.status_code == 302

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT original_note, improved_note FROM clinical_notes WHERE patient_id = ? ORDER BY id DESC LIMIT 1", (patient_id,))
    note_row = cur.fetchone()
    conn.close()
    assert note_row["original_note"] == "Follow-up planned"
    assert note_row["improved_note"] == "Follow-up planned"
