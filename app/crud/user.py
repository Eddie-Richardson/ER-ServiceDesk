# ER-ServiceDesk/app/crud/user.py
# CRUD operations for the User model.
"""
Database access layer for User accounts.

create/update are intentionally NOT implemented here. UserCreate/UserUpdate
carry a plaintext `password` field, not the model's `hashed_password`
column, so a generic dict-unpack create/update would either crash or store
a plaintext password. That logic lives in UserService instead.
"""

from sqlalchemy.orm import Session
from app.models.user import User

class UserCRUD:
    """Direct database access for User records (read/delete only -- see module docstring)."""

    def get(self, db: Session, id: int) -> User | None:
        """
        Fetch a single User by primary key.

        Args:
            db: Active database session.
            id: Primary key of the user to fetch.

        Returns:
            The matching User instance, or None if no record exists.
        """
        return db.query(User).filter(User.id == id).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        """
        Fetch a single User by email -- used to check for a duplicate
        BEFORE attempting to create an account, so a signup attempt
        for an already-registered address fails cleanly up front
        instead of via an unhandled database constraint error later.

        Args:
            db: Active database session.
            email: The email address to look up.

        Returns:
            The matching User instance, or None if no account has this email.
        """
        return db.query(User).filter(User.email == email).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple User records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of User instances.
        """
        return db.query(User).offset(skip).limit(limit).all()

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a User record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the user to delete.
        """
        obj = db.query(User).filter(User.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_user = UserCRUD()
