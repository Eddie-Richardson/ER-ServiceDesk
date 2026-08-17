# ER-ServiceDesk/app/crud/customer.py
# CRUD operations for the Customer model.
"""
Database access layer for a client of the repair shop.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerCRUD:
    """Direct database access for Customer records."""

    def get(self, db: Session, id: int) -> Customer | None:
        return db.query(Customer).filter(Customer.id == id).first()

    def get_by_email(self, db: Session, email: str) -> Customer | None:
        """
        Fetch a single Customer by email address, case-insensitively.

        Used to match an inbound email's sender address back to the
        customer it came from. Case-insensitive because email addresses
        are effectively case-insensitive in practice (most providers
        treat them that way), and a customer's stored
        address may not exactly match the casing their mail client sends.
        """
        return db.query(Customer).filter(Customer.email.ilike(email)).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Customer).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CustomerCreate) -> Customer:
        obj = Customer(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Customer, obj_in: CustomerUpdate) -> Customer:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Customer).filter(Customer.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_customer = CustomerCRUD()
