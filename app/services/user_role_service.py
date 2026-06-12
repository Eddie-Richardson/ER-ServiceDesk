# ER-ServiceDesk/app/services/user_role_service.py
# Service layer for UserRole.
#
# Provides business logic for UserRole operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.user_role import crud_user_role
from app.schemas.user_role import UserRoleCreate, UserRoleUpdate

class UserRoleService:
    # Retrieves a single UserRole by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single UserRole instance.
        """
        return crud_user_role.get(db, id)

    # Retrieves multiple UserRole records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of UserRole records.
        """
        return crud_user_role.get_multi(db, skip, limit)

    # Creates a new UserRole.
    def create(self, db: Session, obj_in: UserRoleCreate):
        """
        Creates a new UserRole using validated input data.
        """
        return crud_user_role.create(db, obj_in)

    # Updates an existing UserRole.
    def update(self, db: Session, id: int, obj_in: UserRoleUpdate):
        """
        Updates an existing UserRole using validated input data.
        """
        db_obj = crud_user_role.get(db, id)
        return crud_user_role.update(db, db_obj, obj_in)

    # Deletes a UserRole by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a UserRole instance.
        """
        return crud_user_role.delete(db, id)

user_role_service = UserRoleService()
