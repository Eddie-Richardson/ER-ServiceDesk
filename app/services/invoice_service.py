# ER-ServiceDesk/app/services/invoice_service.py
# Service layer for Invoice.
"""
Business logic for a bill generated for work performed on a ticket.

Same line-item management pattern as quote_service.py -- add/edit/
remove one at a time, each recalculating subtotal/discount_amount/
tax_amount/total via billing_calculations.calculate_totals().

is_paid is set automatically by payment_service.py whenever a payment
is recorded that brings total payments up to the invoice's own total
-- not something set directly here.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.invoice import crud_invoice
from app.crud.invoice_line_item import crud_invoice_line_item
from app.crud.service import crud_service
from app.crud.discount import crud_discount
from app.crud.tax_rate import crud_tax_rate
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.schemas.invoice_line_item import InvoiceLineItemUpdate
from app.services.billing_calculations import calculate_totals
from app.services.audit_log_service import audit_log_service


class InvoiceService:
    """Business logic for Invoice operations, including line items."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Invoice by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Invoice instance, or None if not found.
        """
        return crud_invoice.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Invoice records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Invoice instances.
        """
        return crud_invoice.get_multi(db, skip, limit)

    def get_by_ticket(self, db: Session, ticket_id: int):
        """
        Fetch every invoice for a given ticket.

        Args:
            db: Active database session.
            ticket_id: The ticket to look up invoices for.

        Returns:
            A list of Invoice instances for that ticket.
        """
        return crud_invoice.get_by_ticket(db, ticket_id)

    def create(self, db: Session, obj_in: InvoiceCreate, current_user_id: int):
        """
        Create a new Invoice directly (not via quote conversion --
        see quote_service.convert_to_invoice() for that path). Starts
        with zero line items and zero totals.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.
            current_user_id: The user creating this invoice -- recorded
                in the audit trail.

        Returns:
            The newly created Invoice instance.
        """
        new_invoice = crud_invoice.create(db, obj_in)
        self._snapshot_discount_and_tax_names(db, new_invoice)

        audit_log_service.log(
            db, "invoice_created", "ticket", new_invoice.ticket_id, user_id=current_user_id,
            details=f"Invoice #{new_invoice.id} created",
        )

        return new_invoice

    def update(self, db: Session, id: int, obj_in: InvoiceUpdate, current_user_id: int):
        """
        Update an existing Invoice's discount/tax selection, details,
        or is_paid. Changing discount_id or tax_rate_id triggers a
        full totals recalculation.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated Invoice instance.
        """
        db_obj = crud_invoice.get(db, id)
        updated = crud_invoice.update(db, db_obj, obj_in)
        self._snapshot_discount_and_tax_names(db, updated)
        self._recalculate(db, updated)

        audit_log_service.log(
            db, "invoice_updated", "ticket", updated.ticket_id, user_id=current_user_id,
            details=f"Invoice #{updated.id} updated",
        )

        return updated

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Delete an Invoice by ID. Its own line items are cascade-deleted
        with it, same reasoning as Quote.delete().

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
            current_user_id: The user performing this deletion --
                recorded in the audit trail.
        """
        db_obj = crud_invoice.get(db, id)
        ticket_id = db_obj.ticket_id if db_obj else None

        result = crud_invoice.delete(db, id)

        if ticket_id is not None:
            audit_log_service.log(
                db, "invoice_deleted", "ticket", ticket_id, user_id=current_user_id,
                details=f"Invoice #{id} deleted",
            )

        return result

    # -----------------------------------------------------------------
    # Line items
    # -----------------------------------------------------------------
    def add_line_item(self, db: Session, invoice_id: int, service_id: int, quantity: int, current_user_id: int):
        """
        Adds a new line item to an invoice, snapshotting the service's
        current name and price, then recalculates totals.

        Args:
            db: Active database session.
            invoice_id: The invoice to add this line item to.
            service_id: The service being added.
            quantity: How many units.
            current_user_id: The user adding this line item -- recorded
                in the audit trail.

        Returns:
            The newly created InvoiceLineItem instance.

        Raises:
            HTTPException: 404 if the service doesn't exist.
        """
        service = crud_service.get(db, service_id)
        if not service:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

        line_item = crud_invoice_line_item.create(db, invoice_id, service_id, service.name, quantity, service.price)

        invoice = crud_invoice.get(db, invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_added", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Added {service.name} x{quantity} (${service.price}) to Invoice #{invoice_id}",
        )

        return line_item

    def update_line_item(self, db: Session, line_item_id: int, obj_in: InvoiceLineItemUpdate, current_user_id: int):
        """
        Updates a line item's quantity, then recalculates totals.

        Args:
            db: Active database session.
            line_item_id: The line item to update.
            obj_in: Fields to change (only quantity is editable).
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated InvoiceLineItem instance.
        """
        db_obj = crud_invoice_line_item.get(db, line_item_id)
        updated = crud_invoice_line_item.update(db, db_obj, obj_in)

        invoice = crud_invoice.get(db, updated.invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_updated", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Updated {updated.service_name} to x{updated.quantity} on Invoice #{updated.invoice_id}",
        )

        return updated

    def remove_line_item(self, db: Session, line_item_id: int, current_user_id: int):
        """
        Removes a line item from an invoice, then recalculates totals.

        Args:
            db: Active database session.
            line_item_id: The line item to remove.
            current_user_id: The user removing this line item --
                recorded in the audit trail.
        """
        db_obj = crud_invoice_line_item.get(db, line_item_id)
        if not db_obj:
            return

        invoice_id = db_obj.invoice_id
        service_name = db_obj.service_name

        crud_invoice_line_item.delete(db, line_item_id)

        invoice = crud_invoice.get(db, invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_removed", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Removed {service_name} from Invoice #{invoice_id}",
        )

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _recalculate(self, db: Session, invoice):
        """
        Recomputes and stores subtotal/discount_amount/tax_amount/total
        from this invoice's current line items and discount/tax
        selection.

        Args:
            db: Active database session.
            invoice: The Invoice instance to recalculate (already loaded).
        """
        line_items = crud_invoice_line_item.get_by_invoice(db, invoice.id)
        discount = crud_discount.get(db, invoice.discount_id) if invoice.discount_id else None
        tax_rate = crud_tax_rate.get(db, invoice.tax_rate_id) if invoice.tax_rate_id else None

        totals = calculate_totals(
            line_items,
            discount.percentage if discount else None,
            tax_rate.percentage if tax_rate else None,
        )

        invoice.subtotal = totals["subtotal"]
        invoice.discount_amount = totals["discount_amount"]
        invoice.tax_amount = totals["tax_amount"]
        invoice.total = totals["total"]
        db.commit()
        db.refresh(invoice)

    def _snapshot_discount_and_tax_names(self, db: Session, invoice):
        """
        Re-snapshots discount_name/tax_rate_name from the currently
        selected Discount/TaxRate -- called whenever discount_id or
        tax_rate_id might have changed.

        Args:
            db: Active database session.
            invoice: The Invoice instance to update (already loaded).
        """
        discount = crud_discount.get(db, invoice.discount_id) if invoice.discount_id else None
        tax_rate = crud_tax_rate.get(db, invoice.tax_rate_id) if invoice.tax_rate_id else None
        invoice.discount_name = discount.name if discount else None
        invoice.tax_rate_name = tax_rate.name if tax_rate else None
        db.commit()
        db.refresh(invoice)

invoice_service = InvoiceService()
