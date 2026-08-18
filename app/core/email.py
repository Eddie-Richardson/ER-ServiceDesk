# ER-ServiceDesk/app/core/email.py
# SMTP (outbound) / IMAP (inbound) email integration.
"""
Email integration over standard SMTP/IMAP -- not tied to any one
provider. Only the connection METHOD is hardcoded (STARTTLS for SMTP,
implicit SSL for IMAP), confirmed close to universal standards across
major providers (Gmail, Outlook/365, Yahoo, iCloud all verified
working). The actual host/port/credentials/business name are real
SystemSetting rows, editable anytime through Settings -> Business Info
-- never .env, never read once at process startup and held stale for
that process's whole lifetime. Every function here takes a db session
and reads these fresh, on every single call, specifically so a
password/host change made through the UI takes effect on the very
next send/poll, not only after every backend process happens to
restart.

Outbound: smtplib with STARTTLS, authenticated with the stored email
password -- for providers like Gmail that require one, this is an App
Password (not the account's real login password; generated separately
and often requiring 2-Step Verification to be enabled first). Other
providers may accept the account's normal password directly instead.
The password itself is stored encrypted at rest (see
app/core/encryption.py, the same mechanism already used for Device
User Account passwords) and only decrypted in memory for the instant
of an actual SMTP/IMAP login.

Inbound: imaplib polling the inbox for unread messages. A customer
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

from sqlalchemy.orm import Session
from app.core.encryption import decrypt_password
from app.services.system_setting_service import system_setting_service


def _get_email_config(db: Session) -> dict:
    """
    Returns:
        A dict with keys: business_name, email_address, email_password
        (decrypted plaintext, or "" if never set), smtp_host, smtp_port,
        imap_host, imap_port.
    """
    encrypted_password = system_setting_service.get_str(db, "email_password_encrypted", "")
    return {
        "business_name": system_setting_service.get_str(db, "business_name", ""),
        "email_address": system_setting_service.get_str(db, "email_address", ""),
        "email_password": decrypt_password(encrypted_password) if encrypted_password else "",
        "smtp_host": system_setting_service.get_str(db, "smtp_host", "smtp.gmail.com"),
        "smtp_port": system_setting_service.get_int(db, "smtp_port", 587),
        "imap_host": system_setting_service.get_str(db, "imap_host", "imap.gmail.com"),
        "imap_port": system_setting_service.get_int(db, "imap_port", 993),
    }

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
    Returns:
        The subject with a "[Ticket #<id>]" prefix, e.g.
        "[Ticket #42] Your repair is ready for pickup".
    """
    return f"[Ticket #{ticket_id}] {subject}"


def extract_ticket_id(subject: str) -> int | None:
    """
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

def send_email(db: Session, to_address: str, subject: str, body: str) -> None:
    """
    Send a plain-text email over SMTP.

    Raises:
        RuntimeError: If email address or password aren't configured
            yet in Settings -> Business Info.
        smtplib.SMTPException: If the send itself fails (auth failure,
            connection issue, etc.) -- allowed to propagate so the caller
            (or an RQ job's retry logic) can decide how to handle it.
    """
    config = _get_email_config(db)
    if not config["email_address"] or not config["email_password"]:
        raise RuntimeError(
            "Email address and password must be set in Settings -> "
            "Business Info before sending email."
        )

    msg = EmailMessage()
    msg["From"] = f"{config['business_name']} <{config['email_address']}>" if config["business_name"] else config["email_address"]
    msg["To"] = to_address
    msg["Subject"] = subject
    if config["business_name"]:
        body = f"{body}\n\n-- \n{config['business_name']}"
    msg.set_content(body)

    with smtplib.SMTP(config["smtp_host"], config["smtp_port"]) as server:
        server.starttls()
        server.login(config["email_address"], config["email_password"])
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


def fetch_unread_emails(db: Session) -> list[InboundEmail]:
    """
    Connect to the inbox via IMAP, fetch all unread messages, and
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
        RuntimeError: If email address or password aren't configured
            yet in Settings -> Business Info.
        imaplib.IMAP4.error: If the IMAP connection/login/fetch fails.
    """
    config = _get_email_config(db)
    if not config["email_address"] or not config["email_password"]:
        raise RuntimeError(
            "Email address and password must be set in Settings -> "
            "Business Info before polling email."
        )

    results: list[InboundEmail] = []

    with imaplib.IMAP4_SSL(config["imap_host"], config["imap_port"]) as imap:
        imap.login(config["email_address"], config["email_password"])
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
