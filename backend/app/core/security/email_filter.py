import re
from typing import Set
from email_validator import validate_email, EmailNotValidError


class InvalidEmailError(ValueError):
    """Raised when an email address does not conform to RFC syntax standards."""
    pass


class DisposableEmailError(ValueError):
    """Raised when an email address originates from a known disposable or burner email domain."""
    pass


# High-frequency disposable, temporary, and burner email domains
DISPOSABLE_DOMAINS: Set[str] = frozenset({
    "10minutemail.com",
    "10minutemail.net",
    "burnermail.io",
    "crazymailing.com",
    "dispostable.com",
    "dropmail.me",
    "emailondeck.com",
    "fakeinbox.com",
    "getairmail.com",
    "getnada.com",
    "grr.la",
    "guerrillamail.biz",
    "guerrillamail.block",
    "guerrillamail.com",
    "guerrillamail.de",
    "guerrillamail.net",
    "guerrillamail.org",
    "guerrillamailblock.com",
    "inboxkitten.com",
    "mailcatch.com",
    "maildrop.cc",
    "mailinator.com",
    "mailnesia.com",
    "mohmal.com",
    "mohmal.im",
    "mohmal.in",
    "mytemp.email",
    "mytempemail.com",
    "nada.ltd",
    "sharklasers.com",
    "spam4.me",
    "temp-mail.org",
    "tempail.com",
    "tempmail.com",
    "tempmail.net",
    "tempmailaddress.com",
    "throwawaymail.com",
    "tmailor.com",
    "trashmail.com",
    "trashmail.net",
    "yopmail.com",
    "yopmail.net",
})


def validate_and_normalize_email(email: str) -> str:
    """
    Validates email syntax, normalizes whitespace and casing, and rejects disposable email providers.

    Args:
        email: Raw email address string.

    Returns:
        Normalized email string (lowercased, trimmed).

    Raises:
        InvalidEmailError: If the syntax is malformed or violates standard email specifications.
        DisposableEmailError: If the domain or parent domain matches a known disposable email provider.
    """
    if not isinstance(email, str):
        raise InvalidEmailError("Email address must be a string.")

    cleaned = email.strip()
    if not cleaned:
        raise InvalidEmailError("Email address cannot be empty.")

    # Guard against invalid dot placements or spacing before full parser
    if cleaned.startswith(".") or cleaned.endswith(".") or ".." in cleaned:
        raise InvalidEmailError("Email contains invalid dot placements.")

    if " " in cleaned:
        raise InvalidEmailError("Email address cannot contain whitespace.")

    parts = cleaned.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise InvalidEmailError("Email must contain exactly one '@' character separating local and domain parts.")

    domain_raw = parts[1]
    if domain_raw.startswith(".") or domain_raw.endswith(".") or ".." in domain_raw:
        raise InvalidEmailError(f"Invalid domain structure: '{domain_raw}'.")

    try:
        # Validate syntax via RFC-compliant parser without network DNS check
        validated = validate_email(cleaned, check_deliverability=False)
        normalized = validated.normalized.lower()
        domain = validated.domain.lower()
    except EmailNotValidError as exc:
        raise InvalidEmailError(f"Malformed email syntax: {exc}") from exc

    # Check the domain and any parent domains against the disposable list
    domain_parts = domain.split(".")
    if len(domain_parts) < 2:
        raise InvalidEmailError(f"Domain '{domain}' must have a top-level domain.")

    for i in range(len(domain_parts) - 1):
        candidate_domain = ".".join(domain_parts[i:])
        if candidate_domain in DISPOSABLE_DOMAINS:
            raise DisposableEmailError(
                f"Registration with disposable email domain '{domain}' is prohibited."
            )

    return normalized
