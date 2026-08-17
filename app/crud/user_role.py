# ER-ServiceDesk/app/crud/user_role.py
# CRUD operations for the UserRole model.
"""
Database access layer for the many-to-many link between users and roles.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.user_role import UserRole
from app.schemas.user_role import UserRoleCreate, UserRoleUpdate

class UserRoleCRUD:
    """Direct database access for UserRole records."""

    def get(self, db: Session, id: int) -> UserRole | None:
        return db.query(UserRole).filter(UserRole.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(UserRole).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: UserRoleCreate) -> UserRole:
        obj = UserRole(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: UserRole, obj_in: UserRoleUpdate) -> UserRole:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(UserRole).filter(UserRole.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_user_role = UserRoleCRUD()
