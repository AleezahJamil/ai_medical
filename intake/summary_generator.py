import json
import datetime
from groq import Groq
import os
from dotenv import load_dotenv
from storage.db import get_connection

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_main_concern(symptoms):
    if not symptoms:
        return "No specific concern recorded."

    prompt = f"""
Given this structured list of patient-reported symptoms, write ONE short,
clinical, human-readable sentence summarizing the main concern for this visit.
Do not add any information not present in the data. Be concise — this is
meant to be scanned in seconds by a doctor.

Symptoms: {json.dumps(symptoms)}

Return only the sentence, nothing else.
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


def build_clinical_summary(checklist_data, safety_flag_level, patient_profile=None):
    main_concern = generate_main_concern(checklist_data)

    summary = {
        "main_concern": main_concern,
        "symptoms": checklist_data,
        "safety_flags": {
            "level": safety_flag_level,
            "requires_review": safety_flag_level in ("URGENT_REVIEW", "EMERGENCY"),
        },
        "patient_profile": patient_profile,
        "doctor_edits": [],
    }
    return summary


def apply_doctor_edit(summary, field_path, new_value, editor_name):
    import datetime

    old_value = _get_nested(summary, field_path)
    _set_nested(summary, field_path, new_value)

    summary["doctor_edits"].append({
        "field": field_path,
        "old_value": old_value,
        "new_value": new_value,
        "editor": editor_name,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    return summary


def _get_nested(data, path):
    keys = path.split(".")
    current = data
    for key in keys:
        if isinstance(current, list):
            current = current[int(key)]
        else:
            current = current.get(key)
    return current


def _set_nested(data, path, value):
    keys = path.split(".")
    current = data
    for key in keys[:-1]:
        current = current[int(key)] if isinstance(current, list) else current[key]
    last_key = keys[-1]
    if isinstance(current, list):
        current[int(last_key)] = value
    else:
        current[last_key] = value


def save_summary_to_db(patient_id, summary):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO summaries (patient_id, summary_json) VALUES (?, ?)",
        (patient_id, json.dumps(summary)),
    )
    conn.commit()
    conn.close()


def save_intake_history_entry(patient_id, summary, completed_at=None, status="Reviewed"):
    conn = get_connection()
    cursor = conn.cursor()
    concern = (summary or {}).get("main_concern") or "No concern recorded"
    completed_at = completed_at or datetime.datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT INTO intake_history (patient_id, concern, completed_at, status) VALUES (?, ?, ?, ?)",
        (patient_id, concern, completed_at, status),
    )
    conn.commit()
    conn.close()


def load_summary_from_db(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT summary_json FROM summaries WHERE patient_id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return json.loads(row["summary_json"])