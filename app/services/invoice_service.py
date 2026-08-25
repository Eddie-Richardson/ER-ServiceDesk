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
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.invoice import crud_invoice
from app.crud.invoice_line_item import crud_invoice_line_item
from app.crud.service import crud_service
from app.crud.part import crud_part
from app.crud.discount import crud_discount
from app.crud.tax_rate import crud_tax_rate
from app.crud.payment import crud_payment
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.schemas.invoice_line_item import InvoiceLineItemUpdate
from app.services.billing_calculations import calculate_totals
from app.services.audit_log_service import audit_log_service
from app.services.part_service import part_service


class InvoiceService:
    """Business logic for Invoice operations, including line items."""

    def get(self, db: Session, id: int):
        return crud_invoice.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_invoice.get_multi(db, skip, limit)

    def get_by_ticket(self, db: Session, ticket_id: int):
        return crud_invoice.get_by_ticket(db, ticket_id)

    def create(self, db: Session, obj_in: InvoiceCreate, current_user_id: int):
        """Creates directly (not via quote conversion -- see quote_service.convert_to_invoice() for that path). Starts with zero line items and zero totals."""
        new_invoice = Invoice(**obj_in.model_dump(), invoice_number=self._next_invoice_number(db))
        db.add(new_invoice)
        db.commit()
        db.refresh(new_invoice)
        self._snapshot_discount_and_tax_names(db, new_invoice)

        audit_log_service.log(
            db, "invoice_created", "ticket", new_invoice.ticket_id, user_id=current_user_id,
            details=f"Invoice #{new_invoice.invoice_number} created",
        )

        return new_invoice

    def update(self, db: Session, id: int, obj_in: InvoiceUpdate, current_user_id: int):
        """Changing discount_id or tax_rate_id triggers a full totals recalculation."""
        db_obj = crud_invoice.get(db, id)
        updated = crud_invoice.update(db, db_obj, obj_in)
        self._snapshot_discount_and_tax_names(db, updated)
        self._recalculate(db, updated)

        audit_log_service.log(
            db, "invoice_updated", "ticket", updated.ticket_id, user_id=current_user_id,
            details=f"Invoice #{updated.invoice_number} updated",
        )

        return updated

    # -----------------------------------------------------------------
    # Line items
    # -----------------------------------------------------------------
    def add_line_item(self, db: Session, invoice_id: int, quantity: int, current_user_id: int, service_id: int | None = None, part_id: int | None = None):
        """
        Adds a service or a real inventory part as a line item,
        snapshotting its current name and price. Adding a PART line
        item is what actually deducts real inventory, at the
        Admin-configured deduction location (SystemSetting
        "part_deduction_location_id") -- a service line never touches
        inventory at all.

        Raises:
            HTTPException: 400 if neither or both of service_id/part_id
                are given. 404 if the referenced service/part doesn't
                exist. 400 if the part has no selling_price configured,
                or no deduction location is configured.
        """
        if (service_id is None) == (part_id is None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide exactly one of service_id or part_id.")

        if service_id is not None:
            service = crud_service.get(db, service_id)
            if not service:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
            line_item = crud_invoice_line_item.create(
                db, invoice_id, quantity, service.price, service_id=service_id, service_name=service.name,
            )
            item_name, item_price = service.name, service.price
        else:
            part = crud_part.get(db, part_id)
            if not part:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
            if part.selling_price is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{part.name}' has no selling price set -- add one in Inventory before billing it.")
            line_item = crud_invoice_line_item.create(
                db, invoice_id, quantity, part.selling_price, part_id=part_id, part_name=part.name,
            )
            item_name, item_price = part.name, part.selling_price
            part_service.deduct_stock(db, part_id, quantity)

        invoice = crud_invoice.get(db, invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_added", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Added {item_name} x{quantity} (${item_price}) to Invoice #{invoice.invoice_number}",
        )

        return line_item

    def update_line_item(self, db: Session, line_item_id: int, obj_in: InvoiceLineItemUpdate, current_user_id: int):
        """Only quantity is editable. Recalculates totals, and adjusts inventory by the delta if this is a part line."""
        db_obj = crud_invoice_line_item.get(db, line_item_id)
        old_quantity = db_obj.quantity
        is_part_line = db_obj.part_id is not None

        updated = crud_invoice_line_item.update(db, db_obj, obj_in)

        if is_part_line and obj_in.quantity is not None and obj_in.quantity != old_quantity:
            delta = obj_in.quantity - old_quantity
            if delta > 0:
                part_service.deduct_stock(db, updated.part_id, delta)
            else:
                part_service.restore_stock(db, updated.part_id, -delta)

        invoice = crud_invoice.get(db, updated.invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_updated", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Updated {updated.service_name or updated.part_name} to x{updated.quantity} on Invoice #{invoice.invoice_number}",
        )

        return updated

    def remove_line_item(self, db: Session, line_item_id: int, current_user_id: int):
        """If this is a part line, restores its deducted inventory before removing it."""
        db_obj = crud_invoice_line_item.get(db, line_item_id)
        if not db_obj:
            return

        invoice_id = db_obj.invoice_id
        item_name = db_obj.service_name or db_obj.part_name

        if db_obj.part_id is not None:
            part_service.restore_stock(db, db_obj.part_id, db_obj.quantity)

        crud_invoice_line_item.delete(db, line_item_id)

        invoice = crud_invoice.get(db, invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_removed", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Removed {item_name} from Invoice #{invoice.invoice_number}",
        )

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Deletes an invoice outright -- the one exception to
        quotes/invoices otherwise never being deletable. Only permitted
        for an accidental, never-touched invoice: no line items yet,
        never emailed, no payments recorded, not the destination of a
        quote conversion (deleting it would leave that quote's
        converted_invoice_id pointing at nothing), and only if it's the
        most recently issued invoice number -- deleting anything but
        the latest would leave a permanent gap in the sequence, which
        is exactly what the independent, sequential numbering exists
        to avoid.

        Raises:
            HTTPException: 404 if the invoice doesn't exist. 400 if it
                fails any of the conditions above.
        """
        invoice = crud_invoice.get(db, id)
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        if crud_invoice_line_item.get_by_invoice(db, id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice has line items and can't be deleted.")
        if invoice.invoice_sent_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice has already been sent and can't be deleted.")
        if invoice.is_paid or crud_payment.get_by_invoice(db, id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice has payments recorded and can't be deleted.")
        if invoice.source_quote_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice came from a converted quote and can't be deleted.")

        most_recent_number = db.query(func.max(Invoice.invoice_number)).scalar()
        if invoice.invoice_number != most_recent_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only the most recently created invoice can be deleted, to avoid leaving a gap in the numbering.")

        audit_log_service.log(
            db, "invoice_deleted", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Deleted unsent, empty Invoice #{invoice.invoice_number}",
        )
        crud_invoice.delete(db, invoice)

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _next_invoice_number(self, db: Session) -> int:
        """
        Returns:
            The next invoice_number to assign: the current highest
            plus one, or 1 if there are no invoices at all. Same
            reasoning as quote_service._next_quote_number() -- delete()
            only ever permits deleting the single most-recently-
            numbered invoice, so max()+1 always correctly reuses
            whatever number was just freed.
        """
        current_max = db.query(func.max(Invoice.invoice_number)).scalar()
        return (current_max or 0) + 1

    def _recalculate(self, db: Session, invoice):
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
        """Called whenever discount_id or tax_rate_id might have changed."""
        discount = crud_discount.get(db, invoice.discount_id) if invoice.discount_id else None
        tax_rate = crud_tax_rate.get(db, invoice.tax_rate_id) if invoice.tax_rate_id else None
        invoice.discount_name = discount.name if discount else None
        invoice.tax_rate_name = tax_rate.name if tax_rate else None
        db.commit()
        db.refresh(invoice)

invoice_service = InvoiceService()
