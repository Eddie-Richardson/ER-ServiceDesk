# ER-ServiceDesk/app/crud/service.py
# CRUD operations for the Service model.
"""
Database access layer for a billable service the shop offers.
"""

from sqlalchemy.orm import Session
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate

class ServiceCRUD:
    """Direct database access for Service records."""

    def get(self, db: Session, id: int) -> Service | None:
        """
        Fetch a single Service by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Service instance, or None if no record exists.
        """
        return db.query(Service).filter(Service.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        """
        Fetch multiple Service records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Service instances.
        """
        return db.query(Service).order_by(Service.name).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ServiceCreate) -> Service:
        """
        Insert a new Service record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Service instance.
        """
        obj = Service(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Service, obj_in: ServiceUpdate) -> Service:
        """
        Apply a partial update to an existing Service record.

        Args:
            db: Active database session.
            db_obj: The existing Service instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Service instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Service record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Service).filter(Service.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_service = ServiceCRUD()
