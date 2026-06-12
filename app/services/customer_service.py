# ER-ServiceDesk/app/services/customer_service.py
# Service layer for Customer.
#
# Provides business logic for Customer operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.customer import crud_customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerService:
    # Retrieves a single Customer by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Customer instance.
        """
        return crud_customer.get(db, id)

    # Retrieves multiple Customer records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Customer records.
        """
        return crud_customer.get_multi(db, skip, limit)

    # Creates a new Customer.
    def create(self, db: Session, obj_in: CustomerCreate):
        """
        Creates a new Customer using validated input data.
        """
        return crud_customer.create(db, obj_in)

    # Updates an existing Customer.
    def update(self, db: Session, id: int, obj_in: CustomerUpdate):
        """
        Updates an existing Customer using validated input data.
        """
        db_obj = crud_customer.get(db, id)
        return crud_customer.update(db, db_obj, obj_in)

    # Deletes a Customer by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Customer instance.
        """
        return crud_customer.delete(db, id)

customer_service = CustomerService()
