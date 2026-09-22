import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timezone
from typing import List, Dict, Any
from app.core.config import get_settings

logger = logging.getLogger("email_service")

# In-memory dispatch audit log (accessible by integration tests and test harness)
sent_verification_emails: List[Dict[str, Any]] = []


def send_verification_email(email: str, code: str) -> None:
    """
    Dispatches a 6-digit OTP verification email via SMTP or records to in-memory dispatch queue.
    """
    settings = get_settings()

    record = {
        "email": email,
        "code": code,
        "timestamp": datetime.now(timezone.utc),
    }
    sent_verification_emails.append(record)

    # Attempt SMTP transmission if a real remote host or credentials are provided
    if settings.SMTP_HOST not in ("localhost", "127.0.0.1", "") or settings.SMTP_USER:
        try:
            msg = EmailMessage()
            msg["Subject"] = "SignalReport Account Verification Code"
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = email
            msg.set_content(
                f"Welcome to SignalReport.\n\n"
                f"Your 6-digit verification code is: {code}\n\n"
                f"This code will expire in 15 minutes. If you did not request this, please ignore."
            )

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
                logger.info(f"Verification email dispatched successfully to {email}")
        except Exception as exc:
            logger.warning(f"Failed to dispatch email over SMTP to {email}: {exc}")
    else:
        logger.info(f"Local environment: verification OTP for {email} recorded to dispatch queue: {code}")
