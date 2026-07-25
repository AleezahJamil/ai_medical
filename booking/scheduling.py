import datetime
import uuid
import json
from storage.db import get_connection


def register_doctor(doctor_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT doctor_id FROM doctors WHERE doctor_id = ?", (doctor_id,))
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO doctors (doctor_id, name, available_slots) VALUES (?, ?, ?)",
            (doctor_id, name, json.dumps([])),
        )
        conn.commit()
    conn.close()
    return {"doctor_id": doctor_id, "name": name}


def add_available_slot(doctor_id, slot_datetime_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT available_slots FROM doctors WHERE doctor_id = ?", (doctor_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"error": "Doctor not found"}
    slots = json.loads(row["available_slots"])
    slots.append(slot_datetime_str)
    cursor.execute("UPDATE doctors SET available_slots = ? WHERE doctor_id = ?", (json.dumps(slots), doctor_id))
    conn.commit()
    conn.close()
    return {"status": "slot added", "slot": slot_datetime_str}


def get_available_slots(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT available_slots FROM doctors WHERE doctor_id = ?", (doctor_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return {"error": "Doctor not found"}
    return {"doctor_id": doctor_id, "available_slots": json.loads(row["available_slots"])}


def book_appointment(patient_id, doctor_id, slot_datetime_str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT available_slots FROM doctors WHERE doctor_id = ?", (doctor_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"error": "Doctor not found"}
    slots = json.loads(row["available_slots"])
    if slot_datetime_str not in slots:
        conn.close()
        return {"error": "This slot is not available"}
    slots.remove(slot_datetime_str)
    cursor.execute("UPDATE doctors SET available_slots = ? WHERE doctor_id = ?", (json.dumps(slots), doctor_id))

    appointment_id = str(uuid.uuid4())
    created_at = datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO appointments (appointment_id, patient_id, doctor_id, slot, status, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (appointment_id, patient_id, doctor_id, slot_datetime_str, "scheduled", created_at),
    )
    conn.commit()
    conn.close()
    return {"status": "booked", "appointment": {
        "appointment_id": appointment_id, "patient_id": patient_id, "doctor_id": doctor_id,
        "slot": slot_datetime_str, "status": "scheduled", "created_at": created_at,
    }}


def get_patient_appointments(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE patient_id = ?", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_doctor_appointments(doctor_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE doctor_id = ? ORDER BY slot ASC", (doctor_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_appointment_completed(appointment_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE appointments SET status = 'completed' WHERE appointment_id = ?", (appointment_id,))
    conn.commit()
    conn.close()
    return {"status": "updated"}


def cancel_appointment(appointment_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"error": "Appointment not found"}
    cursor.execute("UPDATE appointments SET status = 'cancelled' WHERE appointment_id = ?", (appointment_id,))
    cursor.execute("SELECT available_slots FROM doctors WHERE doctor_id = ?", (row["doctor_id"],))
    doc_row = cursor.fetchone()
    slots = json.loads(doc_row["available_slots"])
    slots.append(row["slot"])
    cursor.execute("UPDATE doctors SET available_slots = ? WHERE doctor_id = ?", (json.dumps(slots), row["doctor_id"]))
    conn.commit()
    conn.close()
    return {"status": "cancelled"}