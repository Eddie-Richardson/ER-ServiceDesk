# ER-ServiceDesk/app/services/role_service.py
# Service layer for Role.
#
# Provides business logic for Role operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.role import crud_role
from app.schemas.role import RoleCreate, RoleUpdate

class RoleService:
    # Retrieves a single Role by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Role instance.
        """
        return crud_role.get(db, id)

    # Retrieves multiple Role records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Role records.
        """
        return crud_role.get_multi(db, skip, limit)

    # Creates a new Role.
    def create(self, db: Session, obj_in: RoleCreate):
        """
        Creates a new Role using validated input data.
        """
        return crud_role.create(db, obj_in)

    # Updates an existing Role.
    def update(self, db: Session, id: int, obj_in: RoleUpdate):
        """
        Updates an existing Role using validated input data.
        """
        db_obj = crud_role.get(db, id)
        return crud_role.update(db, db_obj, obj_in)

    # Deletes a Role by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Role instance.
        """
        return crud_role.delete(db, id)

role_service = RoleService()
