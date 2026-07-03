# ER-ServiceDesk/app/services/user_service.py
# Service layer for User.
"""
Business logic for User accounts, including password hashing.

Handles password hashing on create/update, since the User model stores
`hashed_password` but the API schemas only ever accept/expose a plaintext
`password` field. This logic intentionally lives here (not in crud/user.py)
so the CRUD layer stays a generic, dumb data-access layer.
"""

from sqlalchemy.orm import Session
from app.crud.user import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password

class UserService:
    """Business logic for User account operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single User by ID.

        Args:
            db: Active database session.
            id: Primary key of the user to fetch.

        Returns:
            The matching User instance, or None if not found.
        """
        return crud_user.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of User records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of User instances.
        """
        return crud_user.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: UserCreate):
        """
        Create a new User, hashing the plaintext password first.

        Args:
            db: Active database session.
            obj_in: Validated input data, including a plaintext password.

        Returns:
            The newly created User instance.
        """
        user_data = obj_in.dict(exclude={"password"})
        user_data["hashed_password"] = hash_password(obj_in.password)

        db_obj = User(**user_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, id: int, obj_in: UserUpdate):
        """
        Update an existing User, hashing the password if one was provided.

        Args:
            db: Active database session.
            id: Primary key of the user to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated User instance.
        """
        db_obj = crud_user.get(db, id)
        update_data = obj_in.dict(exclude_unset=True)

        if "password" in update_data:
            plaintext = update_data.pop("password")
            update_data["hashed_password"] = hash_password(plaintext)

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int):
        """
        Delete a User by ID.

        Args:
            db: Active database session.
            id: Primary key of the user to delete.
        """
        return crud_user.delete(db, id)

user_service = UserService()
