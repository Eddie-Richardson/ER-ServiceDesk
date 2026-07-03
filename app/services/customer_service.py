# ER-ServiceDesk/app/services/customer_service.py
# Service layer for Customer.
"""
Business logic for a client of the repair shop.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.customer import crud_customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerService:
    """Business logic for Customer operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Customer by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Customer instance, or None if not found.
        """
        return crud_customer.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Customer records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Customer instances.
        """
        return crud_customer.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: CustomerCreate):
        """
        Create a new Customer using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Customer instance.
        """
        return crud_customer.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: CustomerUpdate):
        """
        Update an existing Customer using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Customer instance.
        """
        db_obj = crud_customer.get(db, id)
        return crud_customer.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Customer by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_customer.delete(db, id)

customer_service = CustomerService()
