import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            name TEXT NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(users)")
    existing_columns = [row[1] for row in cursor.fetchall()]
    if "dob" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN dob TEXT DEFAULT ''")
    if "phone" not in existing_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT DEFAULT ''")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS summaries (
            patient_id TEXT PRIMARY KEY,
            summary_json TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intake_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            concern TEXT NOT NULL,
            completed_at TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Reviewed'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            analysis_json TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            doctor_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            available_slots TEXT NOT NULL DEFAULT '[]'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            appointment_id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            slot TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patient_assignments (
            patient_id TEXT PRIMARY KEY,
            doctor_id TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assignment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            assigned_at TEXT NOT NULL,
            unassigned_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clinical_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id TEXT NOT NULL,
            doctor_id TEXT NOT NULL,
            original_note TEXT NOT NULL,
            improved_note TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT ''
        )
    """)

    cursor.execute("PRAGMA table_info(clinical_notes)")
    note_columns = [row[1] for row in cursor.fetchall()]
    if "created_at" not in note_columns:
        cursor.execute("ALTER TABLE clinical_notes ADD COLUMN created_at TEXT NOT NULL DEFAULT ''")
    if "updated_at" not in note_columns:
        cursor.execute("ALTER TABLE clinical_notes ADD COLUMN updated_at TEXT NOT NULL DEFAULT ''")

    conn.commit()
    conn.close()