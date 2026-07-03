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
        """
        Fetch a single Customer by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Customer instance, or None if no record exists.
        """
        return db.query(Customer).filter(Customer.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Customer records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Customer instances.
        """
        return db.query(Customer).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: CustomerCreate) -> Customer:
        """
        Insert a new Customer record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Customer instance.
        """
        obj = Customer(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Customer, obj_in: CustomerUpdate) -> Customer:
        """
        Apply a partial update to an existing Customer record.

        Args:
            db: Active database session.
            db_obj: The existing Customer instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Customer instance.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Customer record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Customer).filter(Customer.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_customer = CustomerCRUD()
