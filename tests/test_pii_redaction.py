from app.llmops.redaction import redact_pii


def test_redacts_an_email_address() -> None:
    assert redact_pii("Contact us at ops@example.com for help.") == (
        "Contact us at [REDACTED_EMAIL] for help."
    )


def test_redacts_a_phone_number() -> None:
    assert redact_pii("Call 555-123-4567 now.") == "Call [REDACTED_PHONE] now."


def test_redacts_an_ssn() -> None:
    assert redact_pii("SSN on file: 123-45-6789.") == "SSN on file: [REDACTED_SSN]."


def test_redacts_a_credit_card_number() -> None:
    assert redact_pii("Card 4111 1111 1111 1111 declined.") == (
        "Card [REDACTED_CARD] declined."
    )


def test_leaves_text_without_pii_unchanged() -> None:
    text = "Invoice total is 1240.00 USD, document type invoice."
    assert redact_pii(text) == text


def test_redacts_multiple_pii_types_in_one_string() -> None:
    text = "Reach jane@example.com or 555-987-6543, SSN 987-65-4321."
    redacted = redact_pii(text)

    assert "jane@example.com" not in redacted
    assert "555-987-6543" not in redacted
    assert "987-65-4321" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted
    assert "[REDACTED_SSN]" in redacted
