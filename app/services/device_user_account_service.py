# ER-ServiceDesk/app/services/device_user_account_service.py
# Service layer for DeviceUserAccount.
"""
Business logic for a login account known to exist on a device.

This is the only layer that calls encrypt_password()/decrypt_password()
-- the route layer and CRUD layer never see plaintext or ciphertext
cross paths incorrectly, since encryption is centralized here.
"""

from sqlalchemy.orm import Session
from app.crud.device_user_account import crud_device_user_account
from app.schemas.device_user_account import DeviceUserAccountCreate, DeviceUserAccountUpdate
from app.core.encryption import encrypt_password, decrypt_password
from app.services.audit_log_service import audit_log_service


class DeviceUserAccountService:
    """Business logic for DeviceUserAccount operations, including password encryption/decryption."""

    def get_by_device(self, db: Session, device_id: int):
        """
        Returns a list of dicts (not ORM instances, since password is
        a computed/decrypted value, not a real column to read
        directly), with passwords decrypted back to plaintext for display.
        """
        accounts = crud_device_user_account.get_by_device(db, device_id)
        return [self._to_response_dict(a) for a in accounts]

    def create(self, db: Session, obj_in: DeviceUserAccountCreate, current_user_id: int):
        """The password itself is never included in the audit log details, only the account name."""
        encrypted = encrypt_password(obj_in.password) if obj_in.password else None
        new_account = crud_device_user_account.create(db, obj_in.device_id, obj_in.account_name, encrypted, obj_in.is_admin)

        audit_log_service.log(
            db, "device_user_account_created", "device", obj_in.device_id, user_id=current_user_id,
            details=f"Added user account: {obj_in.account_name}",
        )

        return self._to_response_dict(new_account)

    def update(self, db: Session, id: int, obj_in: DeviceUserAccountUpdate, current_user_id: int):
        """A new password is encrypted before being written; an unset password leaves the existing one unchanged. Audit log records the account name only, never the password itself."""
        db_obj = crud_device_user_account.get(db, id)
        encrypted = encrypt_password(obj_in.password) if obj_in.password is not None else None
        updated = crud_device_user_account.update(db, db_obj, obj_in.account_name, encrypted, obj_in.is_admin)

        audit_log_service.log(
            db, "device_user_account_updated", "device", updated.device_id, user_id=current_user_id,
            details=f"Updated user account: {updated.account_name}",
        )

        return self._to_response_dict(updated)

    def delete(self, db: Session, id: int, current_user_id: int):
        db_obj = crud_device_user_account.get(db, id)
        device_id = db_obj.device_id if db_obj else None
        account_name = db_obj.account_name if db_obj else None

        result = crud_device_user_account.delete(db, id)

        if device_id is not None:
            audit_log_service.log(
                db, "device_user_account_deleted", "device", device_id, user_id=current_user_id,
                details=f"Removed user account: {account_name}" if account_name else None,
            )

        return result

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _to_response_dict(self, account) -> dict:
        password = decrypt_password(account.encrypted_password) if account.encrypted_password else None
        return {
            "id": account.id,
            "device_id": account.device_id,
            "account_name": account.account_name,
            "password": password,
            "is_admin": account.is_admin,
            "created_at": account.created_at,
            "updated_at": account.updated_at,
        }

device_user_account_service = DeviceUserAccountService()
