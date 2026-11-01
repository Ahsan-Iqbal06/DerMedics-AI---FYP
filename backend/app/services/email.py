"""Outgoing email (password-reset codes).

Configure SMTP in .env (e.g. Gmail with an App Password: smtp.gmail.com, port 587). Without SMTP settings the
message is written to the server log instead, so the reset flow can still be tested locally.
"""

import html as html_lib
import logging
import smtplib
from collections import deque
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger(__name__)

# Last messages "sent" while SMTP isn't configured (used by tests and local development).
DEV_OUTBOX: deque[dict] = deque(maxlen=50)


def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    s = get_settings()
    if not s.smtp_host or not s.smtp_user:
        DEV_OUTBOX.append({"to": to, "subject": subject, "text": text})
        log.warning("SMTP not configured; email to %s not sent.\nSubject: %s\n%s", to, subject, text)
        return
    msg = EmailMessage()
    msg["From"] = s.smtp_from or s.smtp_user
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")
    with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=20) as smtp:
        if s.smtp_use_tls:
            smtp.starttls()
        if s.smtp_user:
            smtp.login(s.smtp_user, s.smtp_password.replace(" ", ""))  # Google shows App Passwords in groups of 4
        smtp.send_message(msg)


def send_reset_code(to: str, name: str, code: str, minutes: int) -> None:
    _send_code_email(
        to, name, code, minutes,
        subject="Your DerMedics AI password reset code",
        intro="Use this code to reset your password:",
        text_intro="Your DerMedics AI password reset code is",
        ignore="If you didn't ask to reset your password, you can ignore this email — your password stays the same.",
    )


def send_verification_code(to: str, name: str, code: str, minutes: int) -> None:
    _send_code_email(
        to, name, code, minutes,
        subject="Confirm your DerMedics AI email",
        intro="Welcome to DerMedics AI! Enter this code in the app to activate your account:",
        text_intro="Your DerMedics AI sign-up code is",
        ignore="If you didn't create a DerMedics AI account, you can ignore this email — no account will be activated.",
    )


def _send_code_email(to: str, name: str, code: str, minutes: int, *, subject: str, intro: str, text_intro: str,
                     ignore: str) -> None:
    text = (
        f"Hi {name},\n\n"
        f"{text_intro}: {code}\n\n"
        f"It expires in {minutes} minutes and can be used once. {ignore}\n\n— DerMedics AI"
    )
    safe_name = html_lib.escape(name)  # names are user-typed: never let them inject links or markup into the email
    html = f"""
    <div style="font-family:Segoe UI,Roboto,Arial,sans-serif;max-width:480px;margin:auto;color:#1E1633">
      <h2 style="color:#6D3FD1;margin-bottom:4px">DerMedics AI</h2>
      <p>Hi {safe_name},</p>
      <p>{intro}</p>
      <p style="font-size:32px;letter-spacing:8px;font-weight:700;background:#EFE8FD;color:#3A1F78;
                padding:14px 0;text-align:center;border-radius:12px">{code}</p>
      <p style="color:#6F6787">It expires in {minutes} minutes and can be used once. {ignore}</p>
    </div>"""
    send_email(to, subject, text, html)
