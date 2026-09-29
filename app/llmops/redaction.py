import re

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_SSN_PATTERN = re.compile(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)")
_CREDIT_CARD_PATTERN = re.compile(r"(?<!\d)\d(?:[ -]?\d){12,18}(?!\d)")
_PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}(?!\d)"
)


def redact_pii(text: str) -> str:
    """Best-effort regex redaction of common PII patterns (email, phone,
    SSN-like, credit-card-like numbers) before text enters logs or traces.

    This is not a comprehensive PII scrubber: it does not detect names,
    addresses, or PII in non-Western formats. It exists to keep obvious
    PII out of observability output (e.g. an LLM trace's error_message),
    not to certify that extracted document text is safe to store or
    display -- that remains a human-review and access-control concern.
    """
    text = _EMAIL_PATTERN.sub("[REDACTED_EMAIL]", text)
    text = _SSN_PATTERN.sub("[REDACTED_SSN]", text)
    text = _CREDIT_CARD_PATTERN.sub("[REDACTED_CARD]", text)
    text = _PHONE_PATTERN.sub("[REDACTED_PHONE]", text)
    return text
