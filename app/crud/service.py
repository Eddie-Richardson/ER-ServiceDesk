# ER-ServiceDesk/app/crud/service.py
"""
Database access layer for a billable service the shop offers.
"""

from sqlalchemy.orm import Session
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceUpdate

class ServiceCRUD:
    """Direct database access for Service records."""

    def get(self, db: Session, id: int) -> Service | None:
        return db.query(Service).filter(Service.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        return db.query(Service).order_by(Service.name).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: ServiceCreate) -> Service:
        obj = Service(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Service, obj_in: ServiceUpdate) -> Service:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Service).filter(Service.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_service = ServiceCRUD()
