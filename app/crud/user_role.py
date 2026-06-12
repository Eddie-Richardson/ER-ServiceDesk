# ER-ServiceDesk/app/crud/user_role.py
# CRUD operations for the UserRole model.
#
# Provides database access for creating, reading, updating, and deleting UserRole records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.user_role import UserRole
from app.schemas.user_role import UserRoleCreate, UserRoleUpdate

class UserRoleCRUD:
    # Retrieves a single UserRole by ID.
    def get(self, db: Session, id: int) -> UserRole | None:
        """
        Returns a single UserRole instance matching the given ID.
        """
        return db.query(UserRole).filter(UserRole.id == id).first()

    # Retrieves multiple UserRole records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of UserRole records with pagination support.
        """
        return db.query(UserRole).offset(skip).limit(limit).all()

    # Creates a new UserRole record.
    def create(self, db: Session, obj_in: UserRoleCreate) -> UserRole:
        """
        Creates a new UserRole using the provided input schema.
        """
        obj = UserRole(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing UserRole record.
    def update(self, db: Session, db_obj: UserRole, obj_in: UserRoleUpdate) -> UserRole:
        """
        Updates the given UserRole instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a UserRole record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the UserRole instance matching the given ID.
        """
        obj = db.query(UserRole).filter(UserRole.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_user_role = UserRoleCRUD()
