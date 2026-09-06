# ER-ServiceDesk/app/crud/permission.py
"""
Database access layer for a single grantable capability in the RBAC system.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

class PermissionCRUD:
    """Direct database access for Permission records."""

    def get(self, db: Session, id: int) -> Permission | None:
        return db.query(Permission).filter(Permission.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Permission).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: PermissionCreate) -> Permission:
        obj = Permission(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Permission, obj_in: PermissionUpdate) -> Permission:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Permission).filter(Permission.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_permission = PermissionCRUD()
