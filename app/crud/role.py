# ER-ServiceDesk/app/crud/role.py
# CRUD operations for the Role model.
#
# Provides database access for creating, reading, updating, and deleting Role records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

class RoleCRUD:
    # Retrieves a single Role by ID.
    def get(self, db: Session, id: int) -> Role | None:
        """
        Returns a single Role instance matching the given ID.
        """
        return db.query(Role).filter(Role.id == id).first()

    # Retrieves multiple Role records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Role records with pagination support.
        """
        return db.query(Role).offset(skip).limit(limit).all()

    # Creates a new Role record.
    def create(self, db: Session, obj_in: RoleCreate) -> Role:
        """
        Creates a new Role using the provided input schema.
        """
        obj = Role(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Role record.
    def update(self, db: Session, db_obj: Role, obj_in: RoleUpdate) -> Role:
        """
        Updates the given Role instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Role record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Role instance matching the given ID.
        """
        obj = db.query(Role).filter(Role.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_role = RoleCRUD()
