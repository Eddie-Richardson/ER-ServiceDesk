# ER-ServiceDesk/app/crud/user.py
# CRUD operations for the User model.
#
# Provides database access for creating, reading, updating, and deleting User records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate

class UserCRUD:
    # Retrieves a single User by ID.
    def get(self, db: Session, id: int) -> User | None:
        """
        Returns a single User instance matching the given ID.
        """
        return db.query(User).filter(User.id == id).first()

    # Retrieves multiple User records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of User records with pagination support.
        """
        return db.query(User).offset(skip).limit(limit).all()

    # Creates a new User record.
    def create(self, db: Session, obj_in: UserCreate) -> User:
        """
        Creates a new User using the provided input schema.
        """
        obj = User(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing User record.
    def update(self, db: Session, db_obj: User, obj_in: UserUpdate) -> User:
        """
        Updates the given User instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a User record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the User instance matching the given ID.
        """
        obj = db.query(User).filter(User.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_user = UserCRUD()
