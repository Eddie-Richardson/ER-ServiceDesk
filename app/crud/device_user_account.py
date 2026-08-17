# ER-ServiceDesk/app/crud/device_user_account.py
# CRUD operations for the DeviceUserAccount model.
"""
Database access layer for a login account known to exist on a device.

Works with encrypted_password directly -- this layer never sees or
handles plaintext; encryption/decryption happens one layer up in
device_user_account_service.py.
"""

from sqlalchemy.orm import Session
from app.models.device_user_account import DeviceUserAccount

class DeviceUserAccountCRUD:
    """Direct database access for DeviceUserAccount records."""

    def get(self, db: Session, id: int) -> DeviceUserAccount | None:
        return db.query(DeviceUserAccount).filter(DeviceUserAccount.id == id).first()

    def get_by_device(self, db: Session, device_id: int):
        return db.query(DeviceUserAccount).filter(DeviceUserAccount.device_id == device_id).all()

    def create(self, db: Session, device_id: int, account_name: str, encrypted_password: str | None, is_admin: bool) -> DeviceUserAccount:
        obj = DeviceUserAccount(
            device_id=device_id, account_name=account_name,
            encrypted_password=encrypted_password, is_admin=is_admin,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: DeviceUserAccount, account_name: str | None, encrypted_password: str | None, is_admin: bool | None) -> DeviceUserAccount:
        """
        Takes explicit fields rather than a schema, since the caller
        (the service layer) has already handled encrypting a new
        password before this is called.
        """
        if account_name is not None:
            db_obj.account_name = account_name
        if encrypted_password is not None:
            db_obj.encrypted_password = encrypted_password
        if is_admin is not None:
            db_obj.is_admin = is_admin
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(DeviceUserAccount).filter(DeviceUserAccount.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_device_user_account = DeviceUserAccountCRUD()
