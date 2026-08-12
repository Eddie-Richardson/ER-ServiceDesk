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
        """
        Fetch a single DeviceUserAccount by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching DeviceUserAccount instance, or None if not found.
        """
        return db.query(DeviceUserAccount).filter(DeviceUserAccount.id == id).first()

    def get_by_device(self, db: Session, device_id: int):
        """
        Fetch every user account known for a given device.

        Args:
            db: Active database session.
            device_id: The device to look up accounts for.

        Returns:
            A list of DeviceUserAccount instances for that device.
        """
        return db.query(DeviceUserAccount).filter(DeviceUserAccount.device_id == device_id).all()

    def create(self, db: Session, device_id: int, account_name: str, encrypted_password: str | None, is_admin: bool) -> DeviceUserAccount:
        """
        Insert a new DeviceUserAccount record.

        Args:
            db: Active database session.
            device_id: The device this account belongs to.
            account_name: The account's username/display name.
            encrypted_password: The already-encrypted password, or None.
            is_admin: Whether this account has administrator privileges.

        Returns:
            The newly created, refreshed DeviceUserAccount instance.
        """
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
        Apply a partial update to an existing DeviceUserAccount record.
        Takes explicit fields rather than a schema, since the caller
        (the service layer) has already handled encrypting a new
        password before this is called.

        Args:
            db: Active database session.
            db_obj: The existing DeviceUserAccount instance to update.
            account_name: New account name, or None to leave unchanged.
            encrypted_password: New already-encrypted password, or
                None to leave unchanged.
            is_admin: New admin flag, or None to leave unchanged.

        Returns:
            The updated, refreshed DeviceUserAccount instance.
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
        """
        Delete a DeviceUserAccount record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(DeviceUserAccount).filter(DeviceUserAccount.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_device_user_account = DeviceUserAccountCRUD()
