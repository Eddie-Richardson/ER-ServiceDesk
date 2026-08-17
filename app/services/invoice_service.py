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
from app.crud.part import crud_part
from app.crud.discount import crud_discount
from app.crud.tax_rate import crud_tax_rate
from app.models.part_location import PartLocation
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate
from app.schemas.invoice_line_item import InvoiceLineItemUpdate
from app.services.billing_calculations import calculate_totals
from app.services.audit_log_service import audit_log_service
from app.services.system_setting_service import system_setting_service


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
        new_invoice = crud_invoice.create(db, obj_in)
        self._snapshot_discount_and_tax_names(db, new_invoice)

        audit_log_service.log(
            db, "invoice_created", "ticket", new_invoice.ticket_id, user_id=current_user_id,
            details=f"Invoice #{new_invoice.id} created",
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
            details=f"Invoice #{updated.id} updated",
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
            self._deduct_part_stock(db, part_id, quantity)

        invoice = crud_invoice.get(db, invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_added", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Added {item_name} x{quantity} (${item_price}) to Invoice #{invoice_id}",
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
                self._deduct_part_stock(db, updated.part_id, delta)
            else:
                self._restore_part_stock(db, updated.part_id, -delta)

        invoice = crud_invoice.get(db, updated.invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_updated", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Updated {updated.service_name or updated.part_name} to x{updated.quantity} on Invoice #{updated.invoice_id}",
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
            self._restore_part_stock(db, db_obj.part_id, db_obj.quantity)

        crud_invoice_line_item.delete(db, line_item_id)

        invoice = crud_invoice.get(db, invoice_id)
        self._recalculate(db, invoice)

        audit_log_service.log(
            db, "invoice_line_item_removed", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Removed {item_name} from Invoice #{invoice_id}",
        )

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _deduction_location_id(self, db: Session) -> int:
        """
        Reads the Admin-configured part_deduction_location_id
        SystemSetting.

        Raises:
            HTTPException: 400 if no deduction location is configured
                -- deliberately a hard failure rather than silently
                skipping the deduction, since a part being billed
                without inventory actually moving would be a silent
                data-integrity problem, not just a missing convenience.
        """
        location_id = system_setting_service.get_int(db, "part_deduction_location_id", 0)
        if not location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No part deduction location is configured -- set one in Settings -> System Settings before billing parts.",
            )
        return location_id

    def _deduct_part_stock(self, db: Session, part_id: int, quantity: int):
        """Creates a zero-quantity PartLocation row at the deduction location first if none exists yet, then deducts."""
        location_id = self._deduction_location_id(db)
        part_location = db.query(PartLocation).filter(
            PartLocation.part_id == part_id, PartLocation.location_id == location_id,
        ).first()
        if not part_location:
            part_location = PartLocation(part_id=part_id, location_id=location_id, quantity=0)
            db.add(part_location)
        part_location.quantity -= quantity
        db.commit()

    def _restore_part_stock(self, db: Session, part_id: int, quantity: int):
        """Reverses a prior deduction -- called when a part line item is removed, or its quantity is reduced."""
        location_id = self._deduction_location_id(db)
        part_location = db.query(PartLocation).filter(
            PartLocation.part_id == part_id, PartLocation.location_id == location_id,
        ).first()
        if not part_location:
            part_location = PartLocation(part_id=part_id, location_id=location_id, quantity=0)
            db.add(part_location)
        part_location.quantity += quantity
        db.commit()

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
