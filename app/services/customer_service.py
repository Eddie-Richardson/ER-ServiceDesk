# ER-ServiceDesk/app/services/customer_service.py
# Service layer for Customer.
"""
Business logic for a client of the repair shop.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import datetime, timezone, timedelta
from app.crud.customer import crud_customer
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.models.device import Device
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.audit_log_service import audit_log_service

class CustomerService:
    """Business logic for Customer operations."""

    def get(self, db: Session, id: int):
        return crud_customer.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_customer.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: CustomerCreate, current_user_id: int):
        """
        Raises:
            HTTPException: 400 if a customer with this email already
                exists. Email is the only field checked -- name isn't
                unique enough (multiple real customers can share one),
                and phone numbers get reassigned/changed over time, so
                checking against either would risk incorrectly
                blocking a genuinely different person.
        """
        if crud_customer.get_by_email(db, obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A customer with this email address already exists.",
            )

        new_customer = crud_customer.create(db, obj_in)
        audit_log_service.log(
            db, "customer_created", "customer", new_customer.id, user_id=current_user_id,
            details=f"Created customer: {new_customer.first_name} {new_customer.last_name}",
        )
        return new_customer

    def update(self, db: Session, id: int, obj_in: CustomerUpdate, current_user_id: int):
        """
        Raises:
            HTTPException: 400 if the email is being changed to one
                already used by a DIFFERENT customer -- same reasoning
                as create()'s own duplicate check.
        """
        db_obj = crud_customer.get(db, id)
        update_data = obj_in.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != db_obj.email:
            existing = crud_customer.get_by_email(db, update_data["email"])
            if existing and existing.id != id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A customer with this email address already exists.",
                )

        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        updated = crud_customer.update(db, db_obj, obj_in)

        if changed_fields:
            audit_log_service.log(
                db, "customer_updated", "customer", id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return updated

    def archive(self, db: Session, id: int, current_user_id: int | None):
        """
        Hides the customer from the active ticket picker and the
        default Customers view, without deleting or hiding anything
        else about them. Fully reversible (see unarchive()). Can be
        triggered manually here, or automatically by
        archive_inactive_customers() once a customer crosses the
        configured inactivity threshold -- current_user_id is None
        for that automatic, system-initiated case.
        """
        db_obj = crud_customer.get(db, id)
        db_obj.is_archived = True
        db.commit()
        db.refresh(db_obj)

        audit_log_service.log(
            db, "customer_archived", "customer", id, user_id=current_user_id,
            details=f"Archived customer: {db_obj.first_name} {db_obj.last_name}",
        )

        return db_obj

    def unarchive(self, db: Session, id: int, current_user_id: int):
        """Reverses archive() -- the customer becomes visible in the active ticket picker and the default Customers view again."""
        db_obj = crud_customer.get(db, id)
        db_obj.is_archived = False
        db.commit()
        db.refresh(db_obj)

        audit_log_service.log(
            db, "customer_unarchived", "customer", id, user_id=current_user_id,
            details=f"Unarchived customer: {db_obj.first_name} {db_obj.last_name}",
        )

        return db_obj

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Deletes the customer only if they have zero tickets and zero
        devices on file -- a customer with real service history
        attached needs that history dealt with first (tickets
        reassigned to the correct customer record if this was a
        duplicate, devices removed), rather than silently disappearing
        along with everything tied to them.

        Raises:
            HTTPException: 400 if this customer has any tickets or
                devices on file.
        """
        ticket_count = db.query(Ticket).filter(Ticket.customer_id == id).count()
        if ticket_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This customer has {ticket_count} ticket(s) on file. Reassign them to the correct customer first.",
            )

        device_count = db.query(Device).filter(Device.customer_id == id).count()
        if device_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This customer has {device_count} device(s) on file. Remove them first.",
            )

        db_obj = crud_customer.get(db, id)
        deleted_name = f"{db_obj.first_name} {db_obj.last_name}" if db_obj else None

        result = crud_customer.delete(db, id)

        audit_log_service.log(
            db, "customer_deleted", "customer", id, user_id=current_user_id,
            details=f"Deleted customer: {deleted_name}" if deleted_name else None,
        )

        return result

    def get_customers_eligible_for_archiving(self, db: Session, threshold_months: int):
        """
        Finds every non-archived customer whose last real activity is
        older than the given threshold -- "last activity" is their
        most recent ticket's created_at, or their own created_at if
        they've never had a single ticket. Used by
        app.workers.tasks.archive_inactive_customers(), the automatic
        backstop alongside the manual Archive action.

        Args:
            threshold_months: How many months of inactivity make a
                customer eligible. Approximated as 30-day months,
                consistent across every calendar month rather than
                needing genuine calendar-aware month arithmetic for
                what's ultimately a coarse, "roughly N months" cutoff.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=threshold_months * 30)

        eligible = []
        for customer in db.query(Customer).filter(Customer.is_archived == False).all():
            most_recent_ticket = (
                db.query(Ticket)
                .filter(Ticket.customer_id == customer.id)
                .order_by(Ticket.created_at.desc())
                .first()
            )
            last_activity = most_recent_ticket.created_at if most_recent_ticket else customer.created_at
            if last_activity.tzinfo is None:
                last_activity = last_activity.replace(tzinfo=timezone.utc)
            if last_activity < cutoff:
                eligible.append(customer)

        return eligible

customer_service = CustomerService()
