# ER-ServiceDesk/app/services/permission_service.py
"""
Business logic for a single grantable capability in the RBAC system.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.permission import crud_permission
from app.schemas.permission import PermissionCreate, PermissionUpdate
from app.models.user import User

class PermissionService:
    """Business logic for Permission operations."""

    def get_user_permission_names(self, user: User) -> set[str]:
        """
        Computes a user's effective permissions by walking their
        assigned roles: User -> UserRole -> Role -> RolePermission ->
        Permission.name. Superusers are NOT special-cased here -- they
        bypass permission checks entirely at the call site (see
        require_permission in app.api.dependencies), since is_superuser
        is a direct flag, deliberately kept separate from the Role
        system so it can't be lost as a side effect of role bookkeeping.

        Returns:
            The set of permission names (e.g. {"tickets.manage"}) this
            user holds through any of their assigned roles.
        """
        names = set()
        for user_role in user.roles:
            for role_permission in user_role.role.role_permissions:
                names.add(role_permission.permission.name)
        return names

    def get(self, db: Session, id: int):
        return crud_permission.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_permission.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: PermissionCreate):
        return crud_permission.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: PermissionUpdate):
        db_obj = crud_permission.get(db, id)
        return crud_permission.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_permission.delete(db, id)

permission_service = PermissionService()
