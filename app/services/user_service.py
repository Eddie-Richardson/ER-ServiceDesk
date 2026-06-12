# ER-ServiceDesk/app/services/user_service.py
# Service layer for User.
#
# Provides business logic for User operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.user import crud_user
from app.schemas.user import UserCreate, UserUpdate

class UserService:
    # Retrieves a single User by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single User instance.
        """
        return crud_user.get(db, id)

    # Retrieves multiple User records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of User records.
        """
        return crud_user.get_multi(db, skip, limit)

    # Creates a new User.
    def create(self, db: Session, obj_in: UserCreate):
        """
        Creates a new User using validated input data.
        """
        return crud_user.create(db, obj_in)

    # Updates an existing User.
    def update(self, db: Session, id: int, obj_in: UserUpdate):
        """
        Updates an existing User using validated input data.
        """
        db_obj = crud_user.get(db, id)
        return crud_user.update(db, db_obj, obj_in)

    # Deletes a User by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a User instance.
        """
        return crud_user.delete(db, id)

user_service = UserService()
