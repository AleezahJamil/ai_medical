import os
import datetime
from groq import Groq
from dotenv import load_dotenv
from storage.db import get_connection

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def improve_note(rough_note):
    if not rough_note or not rough_note.strip():
        return {"error": "Note text is required"}

    prompt = f"""A doctor wrote this rough note:

{rough_note.strip()}

Rewrite it as a professional clinical note. Use only the information
given above — do not add any new facts, symptoms, or details that
were not stated. Keep it concise, 2-4 sentences, in clinical language."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0.3,
    )
    improved_text = response.choices[0].message.content.strip()

    return {
        "original_note": rough_note,
        "improved_note": improved_text,
    }


def save_note_to_db(patient_id, doctor_id, original_note, improved_note, note_id=None):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.datetime.utcnow().isoformat()

    if note_id:
        cursor.execute(
            "UPDATE clinical_notes SET original_note = ?, improved_note = ?, updated_at = ? WHERE id = ? AND patient_id = ? AND doctor_id = ?",
            (original_note, improved_note, now, note_id, patient_id, doctor_id),
        )
    else:
        cursor.execute(
            "INSERT INTO clinical_notes (patient_id, doctor_id, original_note, improved_note, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (patient_id, doctor_id, original_note, improved_note, now, now),
        )
    conn.commit()
    conn.close()


def get_notes_from_db(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, doctor_id, original_note, improved_note, created_at, updated_at FROM clinical_notes WHERE patient_id = ? ORDER BY updated_at DESC, created_at DESC, id DESC",
        (patient_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]