# ER-ServiceDesk/app/crud/role.py
"""
Database access layer for an authorization grouping assigned to users.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

class RoleCRUD:
    """Direct database access for Role records."""

    def get(self, db: Session, id: int) -> Role | None:
        return db.query(Role).filter(Role.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Role).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: RoleCreate) -> Role:
        obj = Role(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Role, obj_in: RoleUpdate) -> Role:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Role).filter(Role.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_role = RoleCRUD()
