# ER-ServiceDesk/app/crud/role_permission.py
"""
Database access layer for the many-to-many link between roles and permissions.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.role_permission import RolePermission
from app.schemas.role_permission import RolePermissionCreate, RolePermissionUpdate

class RolePermissionCRUD:
    """Direct database access for RolePermission records."""

    def get(self, db: Session, id: int) -> RolePermission | None:
        return db.query(RolePermission).filter(RolePermission.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(RolePermission).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: RolePermissionCreate) -> RolePermission:
        obj = RolePermission(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: RolePermission, obj_in: RolePermissionUpdate) -> RolePermission:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(RolePermission).filter(RolePermission.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_role_permission = RolePermissionCRUD()
