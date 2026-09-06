# ER-ServiceDesk/app/services/business_info_service.py
"""
Business logic for managing the shop's business identity and email
configuration as real, database-backed SystemSetting rows -- not
.env, so a change here takes effect on the very next email send/poll,
not only after every backend process happens to restart (see
app/core/email.py, which reads these same keys fresh on every call).

email_password is the one field here that isn't just a plain
SystemSetting value: it's stored encrypted (same mechanism as Device
User Account passwords, see app/core/encryption.py) under the
'email_password_encrypted' key, and is write-only -- get_full() never
decrypts or returns it, only reports whether one is set at all, and
update() only touches it when a genuinely new value is provided,
leaving the existing one untouched on a blank/omitted update.
"""

from sqlalchemy.orm import Session
from app.services.system_setting_service import system_setting_service
from app.core.encryption import encrypt_password
from app.schemas.business_info import BusinessInfoOut, BusinessInfoUpdate

_STRING_KEYS = {
    "business_name": "",
    "business_phone": "",
    "email_address": "",
    "smtp_host": "smtp.gmail.com",
    "imap_host": "imap.gmail.com",
}
_INT_KEYS = {
    "smtp_port": 587,
    "imap_port": 993,
}


class BusinessInfoService:
    """Business logic for the full business info management screen."""

    def get_full(self, db: Session) -> BusinessInfoOut:
        values = {key: system_setting_service.get_str(db, key, default) for key, default in _STRING_KEYS.items()}
        values.update({key: system_setting_service.get_int(db, key, default) for key, default in _INT_KEYS.items()})
        encrypted_password = system_setting_service.get_str(db, "email_password_encrypted", "")
        values["email_password_is_set"] = bool(encrypted_password)
        return BusinessInfoOut(**values)

    def update(self, db: Session, obj_in: BusinessInfoUpdate):
        for key in _STRING_KEYS:
            system_setting_service.upsert(db, key, getattr(obj_in, key))
        for key in _INT_KEYS:
            system_setting_service.upsert(db, key, str(getattr(obj_in, key)))

        if obj_in.email_password:
            encrypted = encrypt_password(obj_in.email_password)
            system_setting_service.upsert(db, "email_password_encrypted", encrypted)

business_info_service = BusinessInfoService()
