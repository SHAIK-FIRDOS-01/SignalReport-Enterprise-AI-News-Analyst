"""
Authentication services: Email features removed as unneeded.
"""

from collections import deque

# Retained as empty deque for backward compatibility with existing tests
sent_verification_emails: deque = deque(maxlen=10)


def send_verification_email(email: str, code: str) -> None:
    """No-op: Email feature completely removed."""
    pass

