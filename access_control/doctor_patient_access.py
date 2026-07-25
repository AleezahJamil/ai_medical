import datetime
from storage.db import get_connection


def assign_doctor(patient_id, doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()

    cursor.execute("SELECT doctor_id FROM patient_assignments WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    current_doctor = row["doctor_id"] if row else None

    if current_doctor == doctor_id:
        conn.close()
        return {"status": "no change", "doctor_id": doctor_id}

    if current_doctor:
        cursor.execute(
            "UPDATE assignment_history SET unassigned_at = ? WHERE patient_id = ? AND doctor_id = ? AND unassigned_at IS NULL",
            (now, patient_id, current_doctor),
        )
        cursor.execute("DELETE FROM patient_assignments WHERE patient_id = ?", (patient_id,))

    cursor.execute("INSERT INTO patient_assignments (patient_id, doctor_id) VALUES (?, ?)", (patient_id, doctor_id))
    cursor.execute(
        "INSERT INTO assignment_history (patient_id, doctor_id, assigned_at, unassigned_at) VALUES (?, ?, ?, NULL)",
        (patient_id, doctor_id, now),
    )
    conn.commit()
    conn.close()
    return {"status": "assigned", "patient_id": patient_id, "doctor_id": doctor_id}


def get_assigned_doctor(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doctor_id FROM patient_assignments WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    return row["doctor_id"] if row else None


def doctor_has_access(patient_id, doctor_id):
    if get_assigned_doctor(patient_id) == doctor_id:
        return True

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT 1 FROM appointments WHERE patient_id = ? AND doctor_id = ? AND status IN ('scheduled','completed') LIMIT 1",
        (patient_id, doctor_id),
    )
    row = cursor.fetchone()
    conn.close()
    return row is not None


def get_doctor_patient_list(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT patient_id FROM patient_assignments WHERE doctor_id = ?", (doctor_id,))
    rows = cursor.fetchall()
    conn.close()
    return [r["patient_id"] for r in rows]


def get_patient_history(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doctor_id, assigned_at, unassigned_at FROM assignment_history WHERE patient_id = ?", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]