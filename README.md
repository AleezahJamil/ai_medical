# 🏥 CareFlow AI

> An AI-powered medical assistance platform connecting intelligent patient intake, safety assessment, medical document processing, and doctor workflows in one application.

CareFlow AI is a full-stack medical assistance application built with Python and Flask. It provides separate patient and doctor workflows, combines LLM-powered functionality with rule-based safety checks, and supports medical document processing.

---

## 🚀 Overview

CareFlow AI is designed to streamline the interaction between patients and healthcare professionals through an integrated digital platform.

The application provides:

- 🤖 AI-assisted patient intake
- 🛡️ Safety and risk assessment
- 📄 Medical document upload and processing
- 👨‍⚕️ Doctor dashboard and patient workflows
- 🔐 Authentication and access control
- ✅ Doctor approval workflow
- 📅 Booking functionality
- 📧 Email functionality
- 📱 Responsive user interface

---

## ✨ Key Features

### 🤖 AI Patient Intake

Patients can interact with an AI-powered intake workflow to provide information about their situation in a structured manner.

### 🛡️ Safety Engine

CareFlow includes a dedicated safety layer designed to evaluate patient information and identify potentially concerning situations before continuing through the workflow.

### 📄 Medical Document Processing

Patients can upload medical documents which can then be processed and analyzed within the application.

### 👨‍⚕️ Doctor Workflow

Doctors have access to dedicated functionality for managing patient-related information and clinical documentation.

### 🔐 Authentication & Access Control

The application includes authentication and role-based access functionality for different types of users.

### ✅ Doctor Approval

Doctor accounts include an approval workflow before access to relevant functionality is granted.

### 📅 Booking

The platform includes functionality for managing doctor/patient booking workflows.

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, Flask |
| AI / LLM | Groq API |
| Frontend | HTML, CSS, JavaScript |
| API / Networking | Flask-CORS, Requests |
| Document Processing | PyPDF |
| Authentication | Google Auth |
| Database | SQLite |
| Configuration | python-dotenv |
| Testing | Pytest |
| Deployment | Gunicorn |

---

## 🏗️ Architecture

CareFlow is organized into modular components, allowing different areas of the application to be maintained independently.

```text
                    ┌─────────────────────┐
                    │     CareFlow AI     │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        Patient Flow      Doctor Flow      Authentication
              │                │                │
              ▼                ▼                ▼
        AI Intake          Dashboard       Access Control
              │                │
              ▼                ▼
       Safety Engine      Patient Data
              │                │
              └────────┬───────┘
                       ▼
             Medical Documents
                       │
                       ▼
                Document Processing


## 📂 Project Structure

CareFlow AI is organized into modular components for authentication, patient intake,
safety assessment, medical documents, doctor workflows, booking, and email services.

```text
ai_medical/
├── access_control/
├── auth/
├── booking/
├── documents/
├── intake/
├── mailer/
├── notes/
├── safety/
├── static/
├── storage/
├── templates/
├── app.py
├── create_admin.py
├── requirements.txt
└── test_*.py
## 📸 Screenshots

### Patient Landing Page

![Patient Landing Page](screenshots/Landing%20Page%20for%20patient)

### AI-Powered Patient Intake

![AI Intake](screenshots/AI%20Intake)

### Medical Document Upload

![Medical Documents](screenshots/Documents)

### Patient Clinical Summary

![Clinical Summary](screenshots/Clinical%20Summary%20of%20Patient)

### Doctor Patient Overview

![Doctor Patient Overview](screenshots/Patient%20overview%20page%20of%20Doctor)

### Clinical Notes

![Clinical Notes](screenshots/Clinical%20Notes)
