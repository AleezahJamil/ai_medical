"""Isolated email-sending module.

Nothing in here knows about users, tokens, sessions, or the database — it
only knows how to send an email given a recipient, a name, and a link.
Auth logic (auth/auth_routes.py) calls send_verification_email() and reacts
to EmailSendError; it never touches the provider API directly.
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
REQUEST_TIMEOUT_SECONDS = 10


class EmailSendError(Exception):
    """Raised whenever a verification email could not be sent.

    The message is safe to log but is intentionally generic — callers must
    never surface str(exc) directly to the end user.
    """


def _is_dev_mode():
    return os.getenv("MAIL_DEV_MODE", "").strip().lower() == "true"


def send_verification_email(to_email, name, verify_url):
    """Send a verification email containing verify_url to to_email.

    Raises EmailSendError if the email could not be sent for any reason
    (missing config, network failure, provider rejection). Never raises a
    raw provider/network exception, and never logs verify_url, the token
    it contains, or any credential.
    """
    if _is_dev_mode():
        # Explicit opt-in only (MAIL_DEV_MODE=true). This is the one deliberate
        # exception to "never log verification links" — it is local-development
        # convenience only, gated behind an env var nobody sets in production.
        print(f"[DEV MODE - not sent] Verification email for {to_email}: {verify_url}")
        return

    api_key = os.getenv("EMAIL_PROVIDER_API_KEY")
    mail_from = os.getenv("MAIL_FROM")
    mail_from_name = os.getenv("MAIL_FROM_NAME", "CareFlow AI")

    if not api_key or not mail_from:
        logger.error("Email send skipped: EMAIL_PROVIDER_API_KEY or MAIL_FROM is not configured.")
        raise EmailSendError("email provider not configured")

    subject = "Verify your CareFlow AI account"
    text_body = (
        f"Hi {name},\n\n"
        "Please verify your email address to activate your CareFlow AI account:\n\n"
        f"{verify_url}\n\n"
        "This link expires in 24 hours. If you didn't create this account, you can ignore this email.\n"
    )
    html_body = (
        f"<p>Hi {name},</p>"
        "<p>Please verify your email address to activate your CareFlow AI account:</p>"
        f'<p><a href="{verify_url}">{verify_url}</a></p>'
        "<p>This link expires in 24 hours. If you didn't create this account, you can ignore this email.</p>"
    )

    payload = {
        "sender": {"email": mail_from, "name": mail_from_name},
        "to": [{"email": to_email, "name": name}],
        "subject": subject,
        "textContent": text_body,
        "htmlContent": html_body,
    }
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        logger.error("Email send failed: network error contacting provider (%s).", type(exc).__name__)
        raise EmailSendError("network error sending email") from exc

    if response.status_code >= 300:
        # Brevo error bodies are a small {"code": "...", "message": "..."} pair,
        # not a secret — logging it turns "401" into "unauthorized: Key not
        # found", which is what actually gets misconfigurations fixed. Never
        # log the request payload, headers, API key, token, or verify link.
        provider_code = None
        try:
            provider_code = response.json().get("code")
        except ValueError:
            pass
        logger.error(
            "Email send failed: provider returned HTTP %s (code=%s).",
            response.status_code,
            provider_code or "unknown",
        )
        raise EmailSendError(f"provider returned status {response.status_code}")
