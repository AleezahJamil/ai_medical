import os
import subprocess
import sys

# Ensure Flask dependencies are available in the selected interpreter.
try:
    import flask
    import flask_cors
except Exception:
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'flask', 'flask-cors', 'werkzeug'])

from werkzeug.security import generate_password_hash
from app import app
from storage.db import get_connection

email = 'doctor-profile-test@example.com'
conn = get_connection()
cursor = conn.cursor()
cursor.execute('DELETE FROM users WHERE email = ?', (email,))
cursor.execute('DELETE FROM doctors WHERE doctor_id = ?', (email,))
cursor.execute('INSERT INTO users (email, password_hash, role, name, phone, dob) VALUES (?, ?, ?, ?, ?, ?)', (email, generate_password_hash('secret'), 'doctor', 'Dr. Test', '555-0100', '1985-02-01'))
conn.commit()
conn.close()

client = app.test_client()
sess = client.session_transaction()
sess['email'] = email
sess['role'] = 'doctor'
sess['name'] = 'Dr. Test'

profile_resp = client.get('/doctor/profile')
settings_resp = client.get('/doctor/settings')
print('PROFILE', profile_resp.status_code, 'doctor profile' in profile_resp.get_data(as_text=True).lower())
print('SETTINGS', settings_resp.status_code, 'doctor settings' in settings_resp.get_data(as_text=True).lower())
