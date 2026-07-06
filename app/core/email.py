# ER-ServiceDesk/app/core/email.py
# Gmail SMTP (outbound) / IMAP (inbound) integration.
"""
Email integration using Gmail directly -- no third-party provider.

Outbound: smtplib over Gmail's SMTP server, authenticated with an App
Password (not the account's real login password; generated separately
in the Google Account security settings, and only usable once 2-Step
Verification is enabled on the account).

Inbound: imaplib polling the Gmail inbox for unread messages. A customer
reply is matched back to the right ticket via a ticket ID embedded in the
subject line -- see `format_ticket_subject` / `extract_ticket_id` below.
Both outbound and inbound use the same subject convention so a customer's
"Reply" in their email client naturally preserves the ticket ID.
"""

import re
import smtplib
import imaplib
import email as email_lib
from email.message import EmailMessage
from email.utils import parseaddr

from app.core.config import settings

# ---------------------------------------------------------------------------
# Subject-line ticket ID convention
# ---------------------------------------------------------------------------
# Outbound messages get a "[Ticket #123]" prefix. Email clients preserve
# this in the subject when a customer hits Reply, which is what lets
# inbound polling match the reply back to the right ticket without any
# special headers or a unique reply-to address per ticket.

_TICKET_SUBJECT_RE = re.compile(r"\[Ticket #(\d+)\]")


def format_ticket_subject(ticket_id: int, subject: str) -> str:
    """
    Prefix a subject line with the ticket ID marker.

    Args:
        ticket_id: The ticket this message belongs to.
        subject: The human-readable subject text.

    Returns:
        The subject with a "[Ticket #<id>]" prefix, e.g.
        "[Ticket #42] Your repair is ready for pickup".
    """
    return f"[Ticket #{ticket_id}] {subject}"


def extract_ticket_id(subject: str) -> int | None:
    """
    Pull the ticket ID out of a subject line, if present.

    Args:
        subject: A raw email subject line (e.g. a customer's reply, which
            may have "Re: " or "Fwd: " prepended by their email client).

    Returns:
        The ticket ID as an int, or None if no "[Ticket #N]" marker is found.
    """
    match = _TICKET_SUBJECT_RE.search(subject or "")
    return int(match.group(1)) if match else None


# ---------------------------------------------------------------------------
# Outbound (SMTP)
# ---------------------------------------------------------------------------

def send_email(to_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email via Gmail's SMTP server.

    Args:
        to_address: Recipient email address.
        subject: Full subject line (use format_ticket_subject first if this
            is tied to a ticket).
        body: Plain-text message body.

    Raises:
        RuntimeError: If GMAIL_ADDRESS or GMAIL_APP_PASSWORD are not
            configured in settings/.env.
        smtplib.SMTPException: If the send itself fails (auth failure,
            connection issue, etc.) -- allowed to propagate so the caller
            (or an RQ job's retry logic) can decide how to handle it.
    """
    if not settings.GMAIL_ADDRESS or not settings.GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env "
            "before sending email."
        )

    msg = EmailMessage()
    msg["From"] = settings.GMAIL_ADDRESS
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(settings.GMAIL_SMTP_HOST, settings.GMAIL_SMTP_PORT) as server:
        server.starttls()
        server.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
        server.send_message(msg)


# ---------------------------------------------------------------------------
# Inbound (IMAP polling)
# ---------------------------------------------------------------------------

class InboundEmail:
    """A single parsed inbound email, ready to be matched to a ticket."""

    def __init__(self, ticket_id: int | None, from_address: str, subject: str, body: str):
        self.ticket_id = ticket_id
        self.from_address = from_address
        self.subject = subject
        self.body = body


def _extract_plain_body(msg: email_lib.message.Message) -> str:
    """
    Pull the plain-text body out of a parsed email message.

    Handles both simple and multipart messages; for multipart, prefers
    the first "text/plain" part and skips attachments.
    """
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            disposition = str(part.get("Content-Disposition", ""))
            if content_type == "text/plain" and "attachment" not in disposition:
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="replace")
        return ""
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace") if payload else ""


def fetch_unread_emails() -> list[InboundEmail]:
    """
    Connect to the Gmail inbox via IMAP, fetch all unread messages, and
    mark them as read.

    Intended to be called from an RQ job on a schedule (polling), not
    directly from a request handler.

    Returns:
        A list of InboundEmail objects, one per unread message found.
        Messages whose subject has no "[Ticket #N]" marker are still
        returned (with ticket_id=None) so the caller can decide how to
        handle an unmatched reply -- e.g. log it for manual triage rather
        than silently dropping it.

    Raises:
        RuntimeError: If GMAIL_ADDRESS or GMAIL_APP_PASSWORD are not
            configured.
        imaplib.IMAP4.error: If the IMAP connection/login/fetch fails.
    """
    if not settings.GMAIL_ADDRESS or not settings.GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "GMAIL_ADDRESS and GMAIL_APP_PASSWORD must be set in .env "
            "before polling email."
        )

    results: list[InboundEmail] = []

    with imaplib.IMAP4_SSL(settings.GMAIL_IMAP_HOST) as imap:
        imap.login(settings.GMAIL_ADDRESS, settings.GMAIL_APP_PASSWORD)
        imap.select("INBOX")

        status, data = imap.search(None, "UNSEEN")
        if status != "OK":
            return results

        message_ids = data[0].split()
        for msg_id in message_ids:
            status, msg_data = imap.fetch(msg_id, "(RFC822)")
            if status != "OK" or not msg_data or msg_data[0] is None:
                continue

            raw_email = msg_data[0][1]
            parsed = email_lib.message_from_bytes(raw_email)

            subject = parsed.get("Subject", "")
            _, from_address = parseaddr(parsed.get("From", ""))
            body = _extract_plain_body(parsed)
            ticket_id = extract_ticket_id(subject)

            results.append(InboundEmail(ticket_id, from_address, subject, body))

    return results
