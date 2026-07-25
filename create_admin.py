"""One-off CLI tool for creating an admin account.

There is deliberately no web-reachable way to create an admin account —
admin is the highest-privilege role in this app, so account creation is a
manual, terminal-only action. Run this from the project root:

    python create_admin.py

The password is read via getpass (never a command-line argument, never
echoed, never stored in shell history).
"""

import getpass
import re
import sys

from werkzeug.security import generate_password_hash

from storage.db import init_db, get_connection

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def main():
    init_db()

    email = input("Admin email: ").strip()
    if not _EMAIL_RE.match(email):
        print("That doesn't look like a valid email address. Aborting.")
        sys.exit(1)

    name = input("Admin display name: ").strip()
    if not name:
        print("A display name is required. Aborting.")
        sys.exit(1)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        conn.close()
        print(f"An account with the email '{email}' already exists. Aborting.")
        sys.exit(1)

    password = getpass.getpass("Admin password: ")
    confirm = getpass.getpass("Confirm password: ")
    if not password:
        conn.close()
        print("Password cannot be empty. Aborting.")
        sys.exit(1)
    if password != confirm:
        conn.close()
        print("Passwords did not match. Aborting.")
        sys.exit(1)

    password_hash = generate_password_hash(password)
    # is_verified=1: admin accounts are created by a human with terminal
    # access, not through the public signup flow, so email ownership
    # verification doesn't apply. doctor_status is left at its table default
    # ('approved') since it's meaningless for a non-doctor role.
    cursor.execute(
        "INSERT INTO users (email, password_hash, role, name, is_verified) VALUES (?, ?, 'admin', ?, 1)",
        (email, password_hash, name),
    )
    conn.commit()
    conn.close()

    print(f"Admin account created for {email}. They can now log in at /login.")


if __name__ == "__main__":
    main()
