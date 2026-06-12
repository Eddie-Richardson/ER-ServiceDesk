# ER-ServiceDesk/app/crud/customer.py
# CRUD operations for the Customer model.
#
# Provides database access for creating, reading, updating, and deleting Customer records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate

class CustomerCRUD:
    # Retrieves a single Customer by ID.
    def get(self, db: Session, id: int) -> Customer | None:
        """
        Returns a single Customer instance matching the given ID.
        """
        return db.query(Customer).filter(Customer.id == id).first()

    # Retrieves multiple Customer records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Customer records with pagination support.
        """
        return db.query(Customer).offset(skip).limit(limit).all()

    # Creates a new Customer record.
    def create(self, db: Session, obj_in: CustomerCreate) -> Customer:
        """
        Creates a new Customer using the provided input schema.
        """
        obj = Customer(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Customer record.
    def update(self, db: Session, db_obj: Customer, obj_in: CustomerUpdate) -> Customer:
        """
        Updates the given Customer instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Customer record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Customer instance matching the given ID.
        """
        obj = db.query(Customer).filter(Customer.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_customer = CustomerCRUD()
