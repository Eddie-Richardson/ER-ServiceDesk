# ER-ServiceDesk/tests/test_fetch_unread_emails.py
"""
Covers fetch_unread_emails' own real IMAP behavior directly, mocking
imaplib.IMAP4_SSL itself -- test_inbound_email.py only ever mocks
fetch_unread_emails away entirely, so it never actually exercises this
function's own real logic at all.

Regression test: fetching with (RFC822) implicitly marks every message
as read the moment it's fetched, regardless of whether it later turns
out to be matched or unmatched -- confirmed on a real mailbox, where an
unmatched test email came back marked read despite poll_inbound_email's
own comment claiming it would be "left as unread." Fixed by fetching
with (BODY.PEEK[]) instead (identical content, no side effect), and
only explicitly marking a message \\Seen via the on_processed callback
once the caller has genuinely decided it was matched.
"""

from unittest.mock import MagicMock, patch

from app.core.email import fetch_unread_emails
from app.services.system_setting_service import system_setting_service


def _configure_email_settings(db):
    """fetch_unread_emails hard-requires a real, configured email address/password."""
    system_setting_service.upsert(db, "email_address", "shop@example.com")
    from app.core.encryption import encrypt_password
    system_setting_service.upsert(db, "email_password_encrypted", encrypt_password("real-password"))


def _make_mock_imap(message_ids: list[bytes], raw_email: bytes):
    """A mock IMAP4_SSL connection returning the given message IDs from search, and the same raw_email content for every fetch."""
    mock_imap = MagicMock()
    mock_imap.__enter__ = lambda self: mock_imap
    mock_imap.__exit__ = lambda self, *args: None
    mock_imap.search.return_value = ("OK", [b" ".join(message_ids)])
    mock_imap.fetch.return_value = ("OK", [(b"1 (BODY[])", raw_email)])
    return mock_imap


_RAW_EMAIL = (
    b"Subject: Re: [Ticket #1] Laptop repair\r\n"
    b"From: customer@example.com\r\n"
    b"\r\n"
    b"Thanks for the update.\r\n"
)


def test_fetch_uses_body_peek_not_rfc822(db):
    """The actual root-cause fix: fetching must use BODY.PEEK[], which never marks a message read as a side effect of merely reading it -- RFC822 does."""
    _configure_email_settings(db)
    mock_imap = _make_mock_imap([b"1"], _RAW_EMAIL)

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        fetch_unread_emails(db)

    fetch_call_args = mock_imap.fetch.call_args
    assert "BODY.PEEK[]" in fetch_call_args[0][1]
    assert "RFC822" not in fetch_call_args[0][1]


def test_a_message_the_callback_marks_matched_is_stored_as_seen(db):
    """When on_processed returns True for a message, that message is genuinely marked \\Seen via imap.store()."""
    _configure_email_settings(db)
    mock_imap = _make_mock_imap([b"1"], _RAW_EMAIL)

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        fetch_unread_emails(db, on_processed=lambda inbound: True)

    mock_imap.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")


def test_a_message_the_callback_leaves_unmatched_is_never_marked_seen(db):
    """When on_processed returns False, imap.store() is never called for that message -- it genuinely stays unread in the real inbox."""
    _configure_email_settings(db)
    mock_imap = _make_mock_imap([b"1"], _RAW_EMAIL)

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        fetch_unread_emails(db, on_processed=lambda inbound: False)

    mock_imap.store.assert_not_called()


def test_no_callback_at_all_marks_nothing_as_seen(db):
    """Calling fetch_unread_emails with no callback at all (the safest possible default) leaves every message unread -- confirms the new default behavior doesn't silently mark things read the way the old, unconditional version did."""
    _configure_email_settings(db)
    mock_imap = _make_mock_imap([b"1"], _RAW_EMAIL)

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        fetch_unread_emails(db)

    mock_imap.store.assert_not_called()


def test_multiple_messages_are_each_judged_independently(db):
    """With two messages, one genuinely matched and one not, only the matched one's real message ID gets marked seen -- confirms the decision is genuinely per-message, not all-or-nothing for the whole batch."""
    _configure_email_settings(db)

    matched_email = (
        b"Subject: Re: [Ticket #1] Laptop repair\r\n"
        b"From: customer@example.com\r\n\r\n"
        b"Thanks!\r\n"
    )
    unmatched_email = (
        b"Subject: Random question, no ticket marker\r\n"
        b"From: someone@example.com\r\n\r\n"
        b"Hi there\r\n"
    )

    def fetch_side_effect(msg_id, _spec):
        content = matched_email if msg_id == b"1" else unmatched_email
        return ("OK", [(b"1 (BODY[])", content)])

    mock_imap = MagicMock()
    mock_imap.__enter__ = lambda self: mock_imap
    mock_imap.__exit__ = lambda self, *args: None
    mock_imap.search.return_value = ("OK", [b"1 2"])
    mock_imap.fetch.side_effect = fetch_side_effect

    # The real, genuine decision: matched only if the actual, parsed
    # subject genuinely has a [Ticket #N] marker -- exactly what
    # poll_inbound_email's own real callback checks for.
    def on_processed(inbound):
        return inbound.ticket_id is not None

    with patch("app.core.email.imaplib.IMAP4_SSL", return_value=mock_imap):
        fetch_unread_emails(db, on_processed=on_processed)

    mock_imap.store.assert_called_once_with(b"1", "+FLAGS", "\\Seen")
