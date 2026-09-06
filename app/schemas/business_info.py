# ER-ServiceDesk/app/schemas/business_info.py
"""
Request/response schemas for managing the shop's business identity and
email configuration -- business name, phone, the email account used
for outbound sends and inbound polling, and its SMTP/IMAP settings.

Deliberately separate from routes/business_info.py, which is a
different, much narrower thing: any logged-in user (including a
low-privilege Client machine) can fetch just the display name. Full
management of every field here, including ever setting a new email
password, is superuser-only -- see routes/business_info_settings.py.
"""

from pydantic import BaseModel

class BusinessInfoOut(BaseModel):
    """
    Schema returned to the client. Deliberately has no password field
    at all, not even an encrypted or masked one -- this is a
    write-only value, never round-tripped back out once set.
    """
    business_name: str
    business_phone: str
    email_address: str
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
    email_password_is_set: bool

class BusinessInfoUpdate(BaseModel):
    """
    Schema for updating business info. email_password is optional and
    write-only: omit it (or send None) to leave the currently-stored
    password unchanged; send a new value to replace it. There is no
    way to fetch the current password back out through this API at
    all -- only ever to set a new one.
    """
    business_name: str
    business_phone: str
    email_address: str
    email_password: str | None = None
    smtp_host: str
    smtp_port: int
    imap_host: str
    imap_port: int
