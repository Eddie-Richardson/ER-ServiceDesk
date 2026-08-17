# ER-ServiceDesk/app/services/role_service.py
# Service layer for Role.
"""
Business logic for an authorization grouping assigned to users.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.role import crud_role
from app.schemas.role import RoleCreate, RoleUpdate

class RoleService:
    """Business logic for Role operations."""

    def get(self, db: Session, id: int):
        return crud_role.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_role.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: RoleCreate):
        return crud_role.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: RoleUpdate):
        db_obj = crud_role.get(db, id)
        return crud_role.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_role.delete(db, id)

role_service = RoleService()
