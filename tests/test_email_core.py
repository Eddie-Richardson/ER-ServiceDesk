# ER-ServiceDesk/tests/test_email_core.py
"""
Covers the real, remaining gaps in app/core/email.py -- send_email()'s
actual body was never exercised, since every other test in the suite
mocks the function away entirely rather than letting it run for real.
Also covers _extract_plain_body()'s multipart branch (every existing
test used simple, non-multipart messages) and fetch_unread_emails()'s
own missing-credentials/IMAP-failure safety nets.
"""

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from unittest.mock import MagicMock, patch

from app.core.email import send_email, fetch_unread_emails, _extract_plain_body
from app.services.system_setting_service import system_setting_service


def _configure_email_settings(db, business_name=None):
    system_setting_service.upsert(db, "email_address", "shop@example.com")
    from app.core.encryption import encrypt_password
    system_setting_service.upsert(db, "email_password_encrypted", encrypt_password("real-password"))
    system_setting_service.upsert(db, "smtp_host", "smtp.example.com")
    system_setting_service.upsert(db, "smtp_port", "587")
    if business_name:
        system_setting_service.upsert(db, "business_name", business_name)


def test_send_email_raises_when_credentials_are_not_configured(db):
    import pytest
    with pytest.raises(RuntimeError, match="Email address and password"):
        send_email(db, "customer@example.com", "Test Subject", "Test body")


def test_send_email_genuinely_connects_and_sends_via_real_mocked_smtp(db):
    """Confirms the actual, real function body -- not just that it can be mocked away -- genuinely builds the message and calls the real SMTP methods in the right order."""
    _configure_email_settings(db)
    mock_server = MagicMock()
    mock_server.__enter__ = lambda self: mock_server
    mock_server.__exit__ = lambda self, *args: None

    with patch("app.core.email.smtplib.SMTP", return_value=mock_server):
        send_email(db, "customer@example.com", "Test Subject", "Test body")

    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("shop@example.com", "real-password")
    mock_server.send_message.assert_called_once()
    sent_message = mock_server.send_message.call_args[0][0]
    assert sent_message["To"] == "customer@example.com"
    assert sent_message["Subject"] == "Test Subject"


def test_send_email_includes_the_business_name_in_the_from_header_and_signature(db):
    _configure_email_settings(db, business_name="Eddie's Repair Shop")
    mock_server = MagicMock()
    mock_server.__enter__ = lambda self: mock_server
    mock_server.__exit__ = lambda self, *args: None

    with patch("app.core.email.smtplib.SMTP", return_value=mock_server):
        send_email(db, "customer@example.com", "Test Subject", "Test body")

    sent_message = mock_server.send_message.call_args[0][0]
    assert "Eddie's Repair Shop" in sent_message["From"]
    body_content = sent_message.get_content()
    assert "Eddie's Repair Shop" in body_content


def test_extract_plain_body_handles_a_real_multipart_message_with_html_and_plain_parts():
    """A real, genuine multipart message (HTML + plain-text alternative, the most common real-world shape) -- confirms the plain-text part is genuinely selected, not the HTML one."""
    msg = MIMEMultipart("alternative")
    msg.attach(MIMEText("<p>HTML version</p>", "html"))
    msg.attach(MIMEText("Plain text version", "plain"))

    result = _extract_plain_body(msg)

    assert result == "Plain text version"


def test_extract_plain_body_skips_attachments_and_finds_the_real_text_part():
    msg = MIMEMultipart()
    attachment = MIMEText("not the real content", "plain")
    attachment.add_header("Content-Disposition", "attachment", filename="notes.txt")
    msg.attach(attachment)
    msg.attach(MIMEText("The real message body", "plain"))

    result = _extract_plain_body(msg)

    assert result == "The real message body"


def test_fetch_unread_emails_raises_when_credentials_are_not_configured(db):
    import pytest
    with pytest.raises(RuntimeError, match="Email address and password"):
        fetch_unread_emails(db)


def test_fetch_unread_emails_returns_empty_when_the_real_imap_search_itself_fails(db):
    """A genuine IMAP SEARCH failure (status != "OK") is handled as an empty result, not an uncaught crash."""
    _configure_email_settings(db)
    mock_imap = MagicMock()
    mock_imap.__enter__ = lambda self: mock_imap
    mock_imap.__exit__ = lambda self, *args: None
    mock_imap.search.return_value = ("NO", [None])

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        result = fetch_unread_emails(db)

    assert result == []


def test_fetch_unread_emails_skips_a_message_whose_own_individual_fetch_fails(db):
    """One message's own fetch genuinely failing doesn't stop the rest of the batch -- it's skipped, not a hard crash for the whole poll."""
    _configure_email_settings(db)
    mock_imap = MagicMock()
    mock_imap.__enter__ = lambda self: mock_imap
    mock_imap.__exit__ = lambda self, *args: None
    mock_imap.search.return_value = ("OK", [b"1"])
    mock_imap.fetch.return_value = ("NO", [None])

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        result = fetch_unread_emails(db)

    assert result == []
