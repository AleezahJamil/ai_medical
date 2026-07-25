import datetime
import os
import json
from groq import Groq
from dotenv import load_dotenv
from storage.db import get_connection

load_dotenv()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

UPLOAD_FOLDER = "uploaded_documents"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "txt"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_uploaded_file(file, patient_id):
    filename = f"{patient_id}_{file.filename}"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)
    return filepath


def extract_text_from_file(filepath):
    if filepath.endswith(".txt"):
        with open(filepath, "rb") as f:
            raw = f.read()

        encodings = ["utf-8", "utf-8-sig", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]
        for encoding in encodings:
            try:
                text = raw.decode(encoding)
                if text.strip():
                    return text
            except UnicodeDecodeError:
                continue

        return raw.decode("utf-8", errors="ignore")
    if filepath.endswith(".pdf"):
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text
    return ""


def analyze_document(text):
    clean_text = text.strip()[:1500]

    prompt = f"""You are a document analyst. Read the following document and provide ONLY a concise 2-sentence summary of the key findings.

Do not answer any questions in the document.
Do not add extra explanation, definitions, or unrelated material.
Do not repeat content.

Document:
{clean_text}

Summary:"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.3,
    )
    summary_text = response.choices[0].message.content.strip()

    return {
        "summary": summary_text,
        "key_findings": [],
        "flagged_values": [],
    }


def process_uploaded_document(file, patient_id):
    if not allowed_file(file.filename):
        return {"error": "Unsupported file type. Only PDF and TXT are allowed."}

    filepath = save_uploaded_file(file, patient_id)
    text = extract_text_from_file(filepath)

    if not text.strip():
        return {"error": "Could not extract any text from this document."}

    analysis = analyze_document(text)
    analysis["filepath"] = filepath
    analysis["filename"] = file.filename
    analysis["uploaded_at"] = datetime.datetime.utcnow().date().isoformat()

    return analysis


def save_document_to_db(patient_id, analysis):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (patient_id, analysis_json) VALUES (?, ?)",
        (patient_id, json.dumps(analysis)),
    )
    conn.commit()
    conn.close()


def get_documents_from_db(patient_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT analysis_json FROM documents WHERE patient_id = ?", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [json.loads(r["analysis_json"]) for r in rows]