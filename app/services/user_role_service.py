# ER-ServiceDesk/app/services/user_role_service.py
"""
Business logic for the many-to-many link between users and roles.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.user_role import crud_user_role
from app.crud.user import crud_user
from app.crud.role import crud_role
from app.schemas.user_role import UserRoleCreate
from app.services.audit_log_service import audit_log_service

class UserRoleService:
    """Business logic for UserRole operations."""

    def get(self, db: Session, id: int):
        return crud_user_role.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_user_role.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: UserRoleCreate, current_user_id: int):
        result = crud_user_role.create(db, obj_in)

        target_user = crud_user.get(db, obj_in.user_id)
        role = crud_role.get(db, obj_in.role_id)
        audit_log_service.log(
            db, "role_granted", "user", obj_in.user_id, user_id=current_user_id,
            details=f"Granted role '{role.name if role else obj_in.role_id}' to {target_user.email if target_user else obj_in.user_id}",
        )

        return result

    def delete(self, db: Session, id: int, current_user_id: int):
        db_obj = crud_user_role.get(db, id)
        target_user_id = db_obj.user_id if db_obj else None
        target_user = crud_user.get(db, db_obj.user_id) if db_obj else None
        role = crud_role.get(db, db_obj.role_id) if db_obj else None

        result = crud_user_role.delete(db, id)

        if target_user_id is not None:
            audit_log_service.log(
                db, "role_revoked", "user", target_user_id, user_id=current_user_id,
                details=f"Revoked role '{role.name if role else '?'}' from {target_user.email if target_user else '?'}",
            )

        return result

user_role_service = UserRoleService()
