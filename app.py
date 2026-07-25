import datetime
import os
from flask import Flask, jsonify, request, session, render_template, redirect, url_for
from flask_cors import CORS
from intake.conversation import IntakeConversation
from intake.summary_generator import apply_doctor_edit, save_summary_to_db, load_summary_from_db, save_intake_history_entry
from auth.auth_routes import (
    auth_bp,
    users as auth_users,
    get_user_from_db,
    update_user_profile,
    update_doctor_professional_info,
    update_doctor_status,
    get_doctors_by_status,
    check_password_hash,
    generate_password_hash,
)
from auth.decorators import require_role, require_approved_doctor
from documents.document_analysis import process_uploaded_document, save_document_to_db, get_documents_from_db
from booking.scheduling import (
    register_doctor, add_available_slot, get_available_slots,
    book_appointment, get_patient_appointments, get_doctor_appointments,
    mark_appointment_completed, cancel_appointment,
)
from storage.db import init_db, get_connection
from access_control.doctor_patient_access import (
    assign_doctor, doctor_has_access, get_doctor_patient_list, get_patient_history, get_assigned_doctor,
)
from notes.clinical_notes import improve_note, save_note_to_db, get_notes_from_db

init_db()

app = Flask(__name__)
CORS(app, supports_credentials=True)
app.secret_key = os.getenv("SECRET_KEY", "change-this-to-a-real-secret-later")
app.register_blueprint(auth_bp)


@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("login_page"))


@app.route("/login", methods=["GET"])
def login_page():
    if "role" in session and "email" in session:
        if session["role"] == "doctor":
            return redirect(url_for("doctor_dashboard_page"))
        if session["role"] == "patient":
            return redirect(url_for("patient_dashboard_page"))
        if session["role"] == "admin":
            return redirect(url_for("admin_dashboard_page"))
    return render_template("login.html")


def compute_age(dob_str):
    if not dob_str:
        return ""
    try:
        parts = dob_str.split("-")
        if len(parts) != 3:
            return ""
        year, month, day = map(int, parts)
        dob = datetime.date(year, month, day)
        today = datetime.date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        return age
    except Exception:
        return ""


def get_user_display_name(user_id):
    if not user_id:
        return "Unknown user"
    user = get_user_from_db(user_id)
    if user and (user.get("name") or "").strip():
        return user["name"].strip()
    return "Unknown user"


@app.route("/patient/dashboard", methods=["GET"])
def patient_dashboard_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))

    patient_id = session["email"]
    appointment_rows = get_patient_appointments(patient_id)

    upcoming = None
    for appointment in sorted(appointment_rows, key=lambda a: a["slot"]):
        if appointment["status"] in ("scheduled", "upcoming"):
            upcoming = appointment
            break
    if not upcoming and appointment_rows:
        upcoming = appointment_rows[0]

    if upcoming:
        appt_doctor = get_user_display_name(upcoming["doctor_id"])
        appt_specialty = "Primary care"
        appt_when = upcoming["slot"]
        appt_location = "Not specified"
    else:
        appt_doctor = "No upcoming appointment"
        appt_specialty = ""
        appt_when = ""
        appt_location = ""

    activity = []
    if appointment_rows:
        for appointment in appointment_rows[-3:][::-1]:
            label = f"Appointment {appointment['status']} with {get_user_display_name(appointment['doctor_id'])}"
            activity.append({"label": label, "at": appointment["slot"]})

    from intake.summary_generator import load_summary_from_db
    summary = load_summary_from_db(patient_id)
    if summary:
        activity.insert(0, {"label": "AI intake summary is ready", "at": "Now"})

    return render_template(
        "patient_dashboard.html",
        first_name=session["name"].split(" ")[0],
        appt_doctor=appt_doctor,
        appt_specialty=appt_specialty,
        appt_when=appt_when,
        appt_location=appt_location,
        activity=activity,
    )


@app.route("/intake/chat", methods=["GET"])
def intake_chat_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))
    return render_template(
        "intake_chat.html",
        patient_id=session["email"],
        first_name=session["name"].split(" ")[0],
    )


@app.route("/patient/clinical-summary", methods=["GET"])
def clinical_summary_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))
    return render_template(
        "clinical_summary.html",
        patient_id=session["email"],
        first_name=session["name"].split(" ")[0],
    )


@app.route("/patient/appointments", methods=["GET"])
def patient_appointments_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))

    patient_id = session["email"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email, name FROM users WHERE role = 'doctor'")
    doctor_names = {row["email"]: (row["name"] or "Unknown doctor").strip() for row in cursor.fetchall()}
    conn.close()

    return render_template(
        "appointments.html",
        patient_id=patient_id,
        first_name=session["name"].split(" ")[0],
        doctor_names=doctor_names,
    )


@app.route("/doctor/dashboard", methods=["GET"])
@require_role("doctor")
def doctor_dashboard_page():
    doctor_id = session.get("email")
    doctor_name = session.get("name")

    doctor_user = get_user_from_db(doctor_id) or {}
    doctor_status = doctor_user.get("doctor_status", "approved")
    if doctor_status != "approved":
        return render_template(
            "doctor_pending.html",
            doctor_id=doctor_id,
            doctor_name=doctor_name,
            doctor_status=doctor_status,
        )

    register_doctor(doctor_id, doctor_name)

    patient_ids = get_doctor_patient_list(doctor_id)
    patient_count = len(patient_ids)

    appointments = get_doctor_appointments(doctor_id)
    now = datetime.datetime.utcnow()
    today_str = now.date().isoformat()
    today_count = sum(
        1 for appt in appointments
        if appt["slot"][:10] == today_str and appt["status"] not in ("cancelled", "completed")
    )

    upcoming = [
        appt for appt in appointments
        if appt["status"] not in ("cancelled", "completed")
        and datetime.datetime.fromisoformat(appt["slot"].replace(" ", "T")) >= now
    ]
    upcoming.sort(key=lambda a: datetime.datetime.fromisoformat(a["slot"].replace(" ", "T")))
    if upcoming:
        next_appt = upcoming[0]
        time_str = datetime.datetime.fromisoformat(next_appt["slot"].replace(" ", "T")).strftime("%I:%M %p").lstrip('0')
        next_appt_summary = f"{get_user_display_name(next_appt['patient_id'])} at {time_str}"
    else:
        next_appt_summary = "None scheduled"

    attention_patients = []
    recent_audit = []

    return render_template(
        "doctor_dashboard.html",
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        specialty="Primary care",
        patient_count=patient_count,
        flagged_count=0,
        today_count=today_count,
        next_appt_summary=next_appt_summary,
        unsigned_count=0,
        attention_patients=attention_patients,
        recent_audit=recent_audit,
    )


@app.route("/doctor/profile", methods=["GET", "POST"])
@require_role("doctor")
def doctor_profile_page():
    doctor_id = session.get("email")
    user = get_user_from_db(doctor_id) or {}
    profile = {
        "name": user.get("name") or session.get("name") or "",
        "email": user.get("email") or doctor_id or "",
        "phone": user.get("phone") or "",
        "dob": user.get("dob") or "",
        "specialty": user.get("doctor_specialty") or "",
        "hospital": user.get("doctor_hospital") or "",
        "license_number": user.get("doctor_license_number") or "",
    }
    doctor_status = user.get("doctor_status", "approved")
    age = compute_age(profile["dob"])
    error = None

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip()
        phone = (request.form.get("phone") or "").strip()
        dob = (request.form.get("dob") or "").strip()
        specialty = (request.form.get("specialty") or "").strip()
        hospital = (request.form.get("hospital") or "").strip()
        license_number = (request.form.get("license_number") or "").strip()

        if not name or not email:
            error = "Name and email are required"
        else:
            result = update_user_profile(
                doctor_id,
                name,
                phone,
                dob,
                new_email=email if email != doctor_id else None,
            )
            if isinstance(result, tuple) and result[0].get("error"):
                error = result[0]["error"]
            else:
                doctor_id = result["email"]
                update_doctor_professional_info(doctor_id, specialty, hospital, license_number)
                session["email"] = doctor_id
                session["name"] = result["name"]
                return redirect(url_for("doctor_profile_page"))

    return render_template(
        "doctor_profile.html",
        doctor_id=doctor_id,
        doctor_name=profile["name"],
        specialty=profile["specialty"],
        hospital=profile["hospital"],
        license_number=profile["license_number"],
        doctor_status=doctor_status,
        name=profile["name"],
        email=profile["email"],
        phone=profile["phone"],
        dob=profile["dob"],
        age=age,
        error=error,
    )


@app.route("/doctor/settings", methods=["GET", "POST"])
@require_role("doctor")
def doctor_settings_page():
    doctor_id = session.get("email")
    user = get_user_from_db(doctor_id) or {}
    profile = {
        "name": user.get("name") or session.get("name") or "",
        "email": user.get("email") or doctor_id or "",
        "phone": user.get("phone") or "",
        "dob": user.get("dob") or "",
    }
    error = None
    success = None

    if request.method == "POST":
        current_password = (request.form.get("current_password") or "").strip()
        new_password = (request.form.get("new_password") or "").strip()
        confirm_password = (request.form.get("confirm_password") or "").strip()

        if not all([current_password, new_password, confirm_password]):
            error = "Please fill in all password fields"
        elif new_password != confirm_password:
            error = "New passwords do not match"
        else:
            stored_user = get_user_from_db(doctor_id) or {}
            if not stored_user or not check_password_hash(stored_user.get("password_hash", ""), current_password):
                error = "Current password is incorrect"
            else:
                password_hash = generate_password_hash(new_password)
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (password_hash, doctor_id))
                conn.commit()
                conn.close()
                success = "Password updated successfully"

    return render_template(
        "doctor_settings.html",
        doctor_id=doctor_id,
        doctor_name=profile["name"],
        specialty=user.get("doctor_specialty") or "",
        name=profile["name"],
        email=profile["email"],
        phone=profile["phone"],
        dob=profile["dob"],
        error=error,
        success=success,
    )


@app.route("/admin/dashboard", methods=["GET"])
@require_role("admin")
def admin_dashboard_page():
    all_doctors = get_doctors_by_status(None)

    status_filter = request.args.get("status")
    if status_filter in ("pending", "approved", "rejected", "suspended"):
        doctors = [d for d in all_doctors if d["doctor_status"] == status_filter]
    else:
        status_filter = "all"
        doctors = all_doctors

    pending_count = sum(1 for d in all_doctors if d["doctor_status"] == "pending")

    return render_template(
        "admin_dashboard.html",
        admin_name=session.get("name"),
        doctors=doctors,
        status_filter=status_filter,
        pending_count=pending_count,
    )


@app.route("/admin/doctor/<doctor_id>/approve", methods=["POST"])
@require_role("admin")
def admin_approve_doctor(doctor_id):
    update_doctor_status(doctor_id, "approved")
    return redirect(url_for("admin_dashboard_page"))


@app.route("/admin/doctor/<doctor_id>/reject", methods=["POST"])
@require_role("admin")
def admin_reject_doctor(doctor_id):
    update_doctor_status(doctor_id, "rejected")
    return redirect(url_for("admin_dashboard_page"))


@app.route("/admin/doctor/<doctor_id>/suspend", methods=["POST"])
@require_role("admin")
def admin_suspend_doctor(doctor_id):
    update_doctor_status(doctor_id, "suspended")
    return redirect(url_for("admin_dashboard_page"))


@app.route("/patient/documents", methods=["GET"])
@app.route("/patient/documents/", methods=["GET"])
def patient_documents_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))
    return render_template(
        "documents.html",
        patient_id=session["email"],
        first_name=session["name"].split(" ")[0],
    )


@app.route("/patient/my-documents", methods=["GET"])
def patient_my_documents_page():
    return patient_documents_page()


@app.route("/patient/my-doctors", methods=["GET"])
def patient_my_doctors_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))

    patient_id = session["email"]
    doctor_id = get_assigned_doctor(patient_id)
    doctors = []

    if doctor_id:
        doctor_user = get_user_from_db(doctor_id) or {}
        doctor_name = (doctor_user.get("name") or doctor_id).strip() or doctor_id
        doctors.append({
            "id": doctor_id,
            "name": doctor_name,
            "specialty": "Primary care",
            "since": "today",
            "nextAppt": "Scheduled",
        })

    return render_template(
        "patient_my_doctors.html",
        first_name=session["name"].split(" ")[0],
        doctors=doctors,
        no_doctors=len(doctors) == 0,
    )


@app.route("/patient/documents/data", methods=["GET"])
def patient_documents_data():
    if session.get("role") != "patient" or "email" not in session:
        return jsonify({"error": "Not logged in"}), 401
    return jsonify(get_documents_from_db(session["email"]))


@app.route("/patient/profile-settings", methods=["GET"])
def patient_profile_settings_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))

    patient_id = session["email"]
    user = get_user_from_db(patient_id)
    summary = load_summary_from_db(patient_id) or {}
    patient_profile = summary.get("patient_profile") or {}
    dob = user.get("dob") or patient_profile.get("dob", "")
    age = compute_age(dob) if dob else patient_profile.get("age", "")

    return render_template(
        "patient_profile_settings.html",
        patient_id=patient_id,
        first_name=session["name"].split(" ")[0],
        name=user["name"],
        email=user["email"],
        phone=user.get("phone", ""),
        dob=dob,
        age=age,
        id=patient_profile.get("mrn", patient_id),
    )


@app.route("/patient/profile-settings", methods=["POST"])
def save_patient_profile_settings():
    if session.get("role") != "patient" or "email" not in session:
        return jsonify({"error": "Not logged in"}), 401

    patient_id = session["email"]
    data = request.json or {}
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    dob = data.get("dob")

    if not name or not email:
        return jsonify({"error": "Name and email are required"}), 400

    result = update_user_profile(patient_id, name, phone or "", dob or "", new_email=email if email != patient_id else None)
    if isinstance(result, tuple) and result[0].get("error"):
        return jsonify(result[0]), result[1]

    session["email"] = result["email"]
    session["name"] = result["name"]
    return jsonify({"status": "saved", **result})


@app.route("/patient/settings", methods=["GET"])
def patient_settings_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))
    return render_template(
        "patient_settings.html",
        first_name=session["name"].split(" ")[0],
        patient_id=session["email"],
    )


@app.route("/patient/intake-history", methods=["GET"])
def patient_intake_history_page():
    if session.get("role") != "patient" or "email" not in session:
        return redirect(url_for("login_page"))

    patient_id = session["email"]
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT concern, completed_at, status FROM intake_history WHERE patient_id = ? ORDER BY completed_at DESC, id DESC",
        (patient_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    history = []
    for row in rows:
        try:
            formatted_date = datetime.datetime.fromisoformat(row["completed_at"].replace(" ", "T")).strftime("%b %d, %Y")
        except ValueError:
            formatted_date = row["completed_at"]
        history.append({
            "concern": row["concern"] or "No concern recorded",
            "date": formatted_date,
            "status": row["status"] or "Reviewed",
        })

    return render_template(
        "patient_intake_history.html",
        first_name=session["name"].split(" ")[0],
        history=history,
        no_history=len(history) == 0,
    )


active_conversations = {}


# ---------- INTAKE ----------

@app.route("/intake/start", methods=["POST"])
def start_intake():
    data = request.json
    patient_id = data.get("patient_id")
    if not patient_id:
        return jsonify({"error": "patient_id is required"}), 400
    active_conversations[patient_id] = IntakeConversation()
    return jsonify({"status": "started", "patient_id": patient_id})


@app.route("/intake/message", methods=["POST"])
def send_message():
    data = request.json
    patient_id = data.get("patient_id")
    message = data.get("message")
    if not patient_id or not message:
        return jsonify({"error": "patient_id and message are required"}), 400
    convo = active_conversations.get(patient_id)
    if not convo:
        return jsonify({"error": "No active conversation for this patient_id"}), 404
    result = convo.process_patient_message(message)
    if result.get("status") == "complete":
        save_summary_to_db(patient_id, result["summary"])
        save_intake_history_entry(patient_id, result["summary"])
    return jsonify(result)


# ---------- DOCTOR SUMMARY VIEW ----------

@app.route("/doctor/summary/<patient_id>", methods=["GET"])
@require_approved_doctor
def get_summary(patient_id):
    doctor_id = session.get("email")
    if not doctor_has_access(patient_id, doctor_id):
        return jsonify({"error": "You do not have access to this patient's records"}), 403
    summary = load_summary_from_db(patient_id)
    if not summary:
        return jsonify({"error": "No summary found for this patient_id"}), 404
    return jsonify(summary)


@app.route("/doctor/summary/<patient_id>/edit", methods=["POST"])
@require_approved_doctor
def edit_summary(patient_id):
    data = request.json or {}
    field_path = data.get("field_path")
    new_value = data.get("new_value")
    editor_name = data.get("editor_name")
    if not all([field_path, new_value, editor_name]):
        return jsonify({"error": "field_path, new_value, and editor_name are required"}), 400
    summary = load_summary_from_db(patient_id)
    if not summary:
        return jsonify({"error": "No summary found for this patient_id"}), 404
    updated_summary = apply_doctor_edit(summary, field_path, new_value, editor_name)
    save_summary_to_db(patient_id, updated_summary)
    return jsonify(updated_summary)


@app.route("/doctor/summary/<patient_id>/save", methods=["POST"])
@require_approved_doctor
def save_summary_text(patient_id):
    doctor_id = session.get("email")
    if not doctor_has_access(patient_id, doctor_id):
        return "Forbidden: You do not have access to this patient's records", 403

    summary_text = request.form.get("summary_text")
    if not summary_text:
        payload = request.get_json(silent=True) or {}
        summary_text = payload.get("summary_text")

    editor_name = request.form.get("editor_name")
    if not editor_name:
        payload = request.get_json(silent=True) or {}
        editor_name = payload.get("editor_name")

    if not summary_text or not editor_name:
        return redirect(url_for("doctor_patient_profile_page", patient_id=patient_id, tab="clinical-summaries"))

    summary = load_summary_from_db(patient_id) or {}
    old_value = summary.get("main_concern")
    summary["main_concern"] = summary_text
    summary.setdefault("doctor_edits", []).append({
        "field": "main_concern",
        "old_value": old_value,
        "new_value": summary_text,
        "editor": editor_name,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    })
    save_summary_to_db(patient_id, summary)
    return redirect(url_for("doctor_patient_profile_page", patient_id=patient_id, tab="clinical-summaries"))


# ---------- DOCUMENT UPLOAD ----------

@app.route("/patient/upload/<patient_id>", methods=["POST"])
def upload_document(patient_id):
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400
    result = process_uploaded_document(file, patient_id)
    if "error" in result:
        return jsonify(result), 400
    save_document_to_db(patient_id, result)
    return jsonify(result)


@app.route("/doctor/documents/<patient_id>", methods=["GET"])
@require_approved_doctor
def get_patient_documents(patient_id):
    doctor_id = session.get("email")
    if not doctor_has_access(patient_id, doctor_id):
        return jsonify({"error": "You do not have access to this patient's documents"}), 403
    return jsonify(get_documents_from_db(patient_id))


# ---------- APPOINTMENT BOOKING ----------

@app.route("/doctor/register", methods=["POST"])
@require_approved_doctor
def doctor_register():
    data = request.json
    doctor_id = data.get("doctor_id")
    name = data.get("name")
    if not doctor_id or not name:
        return jsonify({"error": "doctor_id and name are required"}), 400
    return jsonify(register_doctor(doctor_id, name))


@app.route("/doctor/<doctor_id>/slots", methods=["POST"])
@require_approved_doctor
def add_slot(doctor_id):
    data = request.json
    slot = data.get("slot")
    if not slot:
        return jsonify({"error": "slot is required, format 'YYYY-MM-DD HH:MM'"}), 400
    return jsonify(add_available_slot(doctor_id, slot))


@app.route("/doctor/<doctor_id>/slots", methods=["GET"])
def view_slots(doctor_id):
    return jsonify(get_available_slots(doctor_id))


@app.route("/patient/book", methods=["POST"])
def book():
    data = request.json
    patient_id = data.get("patient_id")
    doctor_id = data.get("doctor_id")
    slot = data.get("slot")
    if not all([patient_id, doctor_id, slot]):
        return jsonify({"error": "patient_id, doctor_id, and slot are required"}), 400

    result = book_appointment(patient_id, doctor_id, slot)
    if result.get("status") == "booked":
        assign_doctor(patient_id, doctor_id)
    return jsonify(result)


@app.route("/patient/<patient_id>/appointments", methods=["GET"])
def patient_appointments(patient_id):
    return jsonify(get_patient_appointments(patient_id))


@app.route("/doctor/appointments", methods=["GET"])
@require_approved_doctor
def doctor_appointments_page():
    doctor_id = session.get("email")
    doctor_name = session.get("name")
    register_doctor(doctor_id, doctor_name)

    appointments = get_doctor_appointments(doctor_id)
    now = datetime.datetime.utcnow()
    current_year = now.year
    current_month = now.month
    first_day = datetime.date(current_year, current_month, 1)
    first_weekday = (first_day.weekday() + 1) % 7
    days_in_month = (datetime.date(current_year, current_month + 1, 1) - datetime.timedelta(days=1)).day if current_month < 12 else (datetime.date(current_year + 1, 1, 1) - datetime.timedelta(days=1)).day

    calendar_cells = []
    for _ in range(first_weekday):
        calendar_cells.append({"day": None, "appts": [], "bg": "#FAFAFD"})

    month_appts_by_day = {}
    upcoming = []

    def get_patient_name(patient_id):
        return get_user_display_name(patient_id)

    for appt in appointments:
        try:
            appt_dt = datetime.datetime.fromisoformat(appt["slot"].replace(" ", "T"))
        except ValueError:
            continue
        appt_date = appt_dt.date()
        display_name = get_patient_name(appt["patient_id"])
        if appt_date.year == current_year and appt_date.month == current_month:
            day = appt_date.day
            month_appts_by_day.setdefault(day, []).append({
                "time": appt_dt.strftime("%I:%M %p").lstrip("0"),
                "patient_name": display_name,
                "status": appt["status"],
                "patient_id": appt["patient_id"],
            })
        if appt_dt >= now and appt["status"] != "cancelled":
            upcoming.append({
                "patient": display_name,
                "patient_id": appt["patient_id"],
                "reason": appt["status"].capitalize(),
                "location": "Office visit",
                "date": appt_dt.strftime("%B %d, %Y"),
                "time": appt_dt.strftime("%I:%M %p").lstrip("0"),
            })

    for day in range(1, days_in_month + 1):
        calendar_cells.append({
            "day": day,
            "appts": month_appts_by_day.get(day, []),
            "bg": "#F4F2FC" if month_appts_by_day.get(day) else "#FFFFFF",
        })
    while len(calendar_cells) % 7 != 0:
        calendar_cells.append({"day": None, "appts": [], "bg": "#FAFAFD"})

    return render_template(
        "doctor_appointments.html",
        doctor_id=doctor_id,
        doctor_name=doctor_name,
        month=now.strftime("%B %Y"),
        weekdays=["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        calendar_cells=calendar_cells,
        upcoming=upcoming,
    )


@app.route("/doctor/patients", methods=["GET"])
@require_approved_doctor
def doctor_patients_page():
    doctor_id = session.get("email")
    doctor_name = session.get("name")
    register_doctor(doctor_id, doctor_name)

    patient_ids = get_doctor_patient_list(doctor_id)
    patients = []
    conn = get_connection()
    cursor = conn.cursor()

    for patient_id in patient_ids:
        cursor.execute(
            "SELECT name, email FROM users WHERE email = ? AND role = 'patient'",
            (patient_id,),
        )
        row = cursor.fetchone()
        if not row:
            continue

        cursor.execute(
            "SELECT slot FROM appointments WHERE patient_id = ? AND doctor_id = ? AND status = 'completed' ORDER BY slot DESC LIMIT 1",
            (patient_id, doctor_id),
        )
        appt_row = cursor.fetchone()
        last_visit = "No visits yet"
        if appt_row and appt_row["slot"]:
            try:
                last_visit_dt = datetime.datetime.fromisoformat(appt_row["slot"].replace(" ", "T"))
                last_visit = last_visit_dt.strftime("%B %d, %Y")
            except ValueError:
                last_visit = appt_row["slot"]

        patients.append({
            "id": patient_id,
            "name": row["name"],
            "email": row["email"],
            "last_visit": last_visit,
        })

    conn.close()
    return render_template("doctor_patients.html", patients=patients)


@app.route("/doctor/audit", methods=["GET"])
@require_approved_doctor
def doctor_audit_page():
    doctor_id = session.get("email")
    doctor_name = session.get("name")
    register_doctor(doctor_id, doctor_name)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT patient_id, assigned_at, unassigned_at FROM assignment_history WHERE doctor_id = ? ORDER BY assigned_at DESC LIMIT 50",
        (doctor_id,),
    )
    rows = cursor.fetchall()

    events = []
    for row in rows:
        cursor.execute("SELECT name FROM users WHERE email = ?", (row["patient_id"],))
        patient_row = cursor.fetchone()
        patient_name = patient_row["name"] if patient_row else row["patient_id"]
        status = "Active" if row["unassigned_at"] is None else "Unassigned"
        events.append({
            "at": row["assigned_at"],
            "patient_id": row["patient_id"],
            "patient_name": patient_name,
            "doctor_id": doctor_id,
            "doctor_name": doctor_name,
            "type": "Assignment",
            "status": status,
        })
    conn.close()

    return render_template("doctor_audit.html", events=events)


@app.route("/doctor/patient/<patient_id>", methods=["GET"])
@require_approved_doctor
def doctor_patient_profile_page(patient_id):
    doctor_id = session.get("email")
    if not doctor_has_access(patient_id, doctor_id):
        return "Forbidden: You do not have access to this patient's records", 403

    tab = request.args.get("tab", "overview")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ? AND role = 'patient'", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return "Patient not found", 404

    summary = load_summary_from_db(patient_id) or {}
    appointments = get_patient_appointments(patient_id)
    now = datetime.datetime.utcnow()
    past_slots = []
    future_slots = []
    for appt in appointments:
        try:
            appt_dt = datetime.datetime.fromisoformat(appt["slot"].replace(" ", "T"))
        except ValueError:
            continue
        if appt_dt < now:
            past_slots.append(appt_dt)
        elif appt["status"] != "cancelled":
            future_slots.append(appt_dt)

    last_visit = max(past_slots).strftime("%B %d, %Y") if past_slots else "No visits yet"
    next_visit = min(future_slots).strftime("%B %d, %Y") if future_slots else "No upcoming visits"

    documents = []
    for doc in get_documents_from_db(patient_id):
        documents.append({
            "name": doc.get("filename") or doc.get("filepath") or "Document",
            "uploadedAt": doc.get("uploaded_at") or doc.get("uploadedAt") or "Unknown",
            "summary": doc.get("summary") or doc.get("analysis") or "No analysis summary available.",
        })

    symptoms = []
    for symptom in summary.get("symptoms", []):
        if isinstance(symptom, dict):
            symptoms.append({
                "label": symptom.get("label") or symptom.get("name") or "Symptom",
                "detail": symptom.get("detail") or symptom.get("value") or "",
                "flagged": bool(symptom.get("flagged") or str(symptom.get("severity", "")).lower() in ("high", "urgent", "true")),
            })
        else:
            symptoms.append({"label": str(symptom), "detail": "", "flagged": False})

    intake_history = []
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT concern, completed_at, status FROM intake_history WHERE patient_id = ? ORDER BY completed_at DESC, id DESC",
        (patient_id,),
    )
    for history_row in cursor.fetchall():
        try:
            formatted_date = datetime.datetime.fromisoformat(history_row["completed_at"].replace(" ", "T")).strftime("%b %d, %Y")
        except ValueError:
            formatted_date = history_row["completed_at"]
        intake_history.append({
            "concern": history_row["concern"] or "No concern recorded",
            "date": formatted_date,
            "status": history_row["status"] or "Reviewed",
        })
    conn.close()

    clinical_notes = get_notes_from_db(patient_id)

    return render_template(
        "doctor_patient_profile.html",
        patient={"id": patient_id, "name": row["name"]},
        avatar="".join([part[0] for part in row["name"].split()[:2]]).upper(),
        mrn=(summary.get("patient_profile") or {}).get("mrn", patient_id),
        age=(summary.get("patient_profile") or {}).get("age", "Unknown"),
        concern=summary.get("main_concern", "No clinical summary available yet."),
        lastVisit=last_visit,
        nextVisit=next_visit,
        symptoms=symptoms,
        documents=documents,
        noDocuments=len(documents) == 0,
        intakeHistory=intake_history,
        noIntakeHistory=len(intake_history) == 0,
        clinicalNotes=clinical_notes,
        noClinicalNotes=len(clinical_notes) == 0,
        activeTab=tab,
    )


@app.route("/doctor/<doctor_id>/appointments", methods=["GET"])
@require_approved_doctor
def doctor_appointments(doctor_id):
    return jsonify(get_doctor_appointments(doctor_id))


@app.route("/appointment/<appointment_id>/complete", methods=["POST"])
@require_approved_doctor
def complete_appointment(appointment_id):
    return jsonify(mark_appointment_completed(appointment_id))


@app.route("/appointment/<appointment_id>/cancel", methods=["POST"])
def cancel(appointment_id):
    return jsonify(cancel_appointment(appointment_id))


# ---------- DOCTOR-PATIENT ACCESS CONTROL ----------

@app.route("/patient/<patient_id>/assign", methods=["POST"])
@require_approved_doctor
def assign_patient(patient_id):
    data = request.json
    doctor_id = data.get("doctor_id")
    if not doctor_id:
        return jsonify({"error": "doctor_id is required"}), 400
    return jsonify(assign_doctor(patient_id, doctor_id))


@app.route("/doctor/<doctor_id>/patients", methods=["GET"])
@require_approved_doctor
def doctor_patient_list(doctor_id):
    return jsonify(get_doctor_patient_list(doctor_id))


@app.route("/patient/<patient_id>/history", methods=["GET"])
@require_approved_doctor
def patient_assignment_history(patient_id):
    return jsonify(get_patient_history(patient_id))


# ---------- CLINICAL NOTES ----------

@app.route("/doctor/notes/<patient_id>/improve", methods=["POST"])
@require_approved_doctor
def improve_clinical_note(patient_id):
    data = request.json or {}
    rough_note = data.get("note")
    if not rough_note:
        return jsonify({"error": "note is required"}), 400
    doctor_id = session.get("email")
    if not doctor_has_access(patient_id, doctor_id):
        return jsonify({"error": "You do not have access to this patient's records"}), 403
    result = improve_note(rough_note)
    if "error" in result:
        return jsonify(result), 400
    result["doctor_id"] = doctor_id
    return jsonify(result)


@app.route("/doctor/notes/<patient_id>", methods=["GET", "POST"])
@require_approved_doctor
def doctor_notes(patient_id):
    doctor_id = session.get("email")
    if not doctor_has_access(patient_id, doctor_id):
        return "Forbidden: You do not have access to this patient's records", 403

    if request.method == "POST":
        note_text = request.form.get("note_text")
        note_id = request.form.get("note_id")
        if not note_text:
            payload = request.get_json(silent=True) or {}
            note_text = payload.get("note_text")
            note_id = payload.get("note_id")
        if note_text:
            save_note_to_db(patient_id, doctor_id, note_text, note_text, note_id=int(note_id) if note_id else None)
        return redirect(url_for("doctor_patient_profile_page", patient_id=patient_id, tab="clinical-notes"))

    return jsonify(get_notes_from_db(patient_id))

@app.route("/patient/summary/<patient_id>", methods=["GET"])
def get_patient_summary(patient_id):
    if session.get("email") != patient_id:
        return jsonify({"error": "You can only view your own summary"}), 403
    summary = load_summary_from_db(patient_id)
    if not summary:
        return jsonify({"error": "No summary found"}), 404
    return jsonify(summary)


# ---------- ENTRY POINT (must stay last) ----------

if __name__ == "__main__":
    app.run(debug=True)