# ER-ServiceDesk/app/services/quote_service.py
"""
Business logic for a cost estimate given to a customer before work is
approved.

Line items are managed here, not through Quote's own update() -- the
same expandable-list pattern as TicketPart (add/edit/remove one at a
time via their own dedicated actions), rather than bulk-replacing a
list through the parent record.

Every action that changes a quote's line items or its discount/tax
selection recalculates subtotal/discount_amount/tax_amount/total via
billing_calculations.calculate_totals() and re-snapshots the
discount/tax names -- these are never computed lazily on read, so
totals stay fast to query and remain accurate even if a Discount/
TaxRate is later renamed or deleted.
"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.crud.quote import crud_quote
from app.crud.quote_line_item import crud_quote_line_item
from app.crud.service import crud_service
from app.models.quote import Quote
from app.crud.part import crud_part
from app.crud.discount import crud_discount
from app.crud.tax_rate import crud_tax_rate
from app.crud.invoice import crud_invoice
from app.crud.invoice_line_item import crud_invoice_line_item
from app.models.invoice import Invoice
from app.schemas.quote import QuoteCreate, QuoteUpdate
from app.schemas.quote_line_item import QuoteLineItemUpdate
from app.services.billing_calculations import calculate_totals
from app.services.audit_log_service import audit_log_service
from app.services.part_service import part_service


class QuoteService:
    """Business logic for Quote operations, including line items and conversion to an Invoice."""

    def get(self, db: Session, id: int):
        return crud_quote.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_quote.get_multi(db, skip, limit)

    def get_by_ticket(self, db: Session, ticket_id: int):
        return crud_quote.get_by_ticket(db, ticket_id)

    def create(self, db: Session, obj_in: QuoteCreate, current_user_id: int):
        """Starts with zero line items and zero totals -- add_line_item() builds it up from there."""
        new_quote = Quote(**obj_in.model_dump(), quote_number=self._next_quote_number(db))
        db.add(new_quote)
        db.commit()
        db.refresh(new_quote)
        self._snapshot_discount_and_tax_names(db, new_quote)

        audit_log_service.log(
            db, "quote_created", "ticket", new_quote.ticket_id, user_id=current_user_id,
            details=f"Quote #{new_quote.quote_number} created",
        )

        return new_quote

    def update(self, db: Session, id: int, obj_in: QuoteUpdate, current_user_id: int):
        """Changing discount_id or tax_rate_id triggers a full totals recalculation."""
        db_obj = crud_quote.get(db, id)
        updated = crud_quote.update(db, db_obj, obj_in)
        self._snapshot_discount_and_tax_names(db, updated)
        self._recalculate(db, updated)

        audit_log_service.log(
            db, "quote_updated", "ticket", updated.ticket_id, user_id=current_user_id,
            details=f"Quote #{updated.quote_number} updated",
        )

        return updated

    # -----------------------------------------------------------------
    # Line items
    # -----------------------------------------------------------------
    def add_line_item(self, db: Session, quote_id: int, quantity: int, current_user_id: int, service_id: int | None = None, part_id: int | None = None):
        """
        Adds a service or a real inventory part as a line item,
        snapshotting its current name and price. Never touches
        inventory -- a quote isn't a real transaction yet; see
        invoice_service.add_line_item() for where part deduction
        actually happens.

        Raises:
            HTTPException: 400 if neither or both of service_id/part_id
                are given. 404 if the referenced service/part doesn't
                exist. 400 if the part has no selling_price configured.
        """
        if (service_id is None) == (part_id is None):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide exactly one of service_id or part_id.")

        if service_id is not None:
            service = crud_service.get(db, service_id)
            if not service:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
            line_item = crud_quote_line_item.create(
                db, quote_id, quantity, service.price, service_id=service_id, service_name=service.name,
            )
            item_name, item_price = service.name, service.price
        else:
            part = crud_part.get(db, part_id)
            if not part:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Part not found")
            if part.selling_price is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"'{part.name}' has no selling price set -- add one in Inventory before billing it.")
            line_item = crud_quote_line_item.create(
                db, quote_id, quantity, part.selling_price, part_id=part_id, part_name=part.name,
            )
            item_name, item_price = part.name, part.selling_price

        quote = crud_quote.get(db, quote_id)
        self._recalculate(db, quote)

        audit_log_service.log(
            db, "quote_line_item_added", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Added {item_name} x{quantity} (${item_price}) to Quote #{quote.quote_number}",
        )

        return line_item

    def update_line_item(self, db: Session, line_item_id: int, obj_in: QuoteLineItemUpdate, current_user_id: int):
        """Only quantity is editable. Recalculates totals after."""
        db_obj = crud_quote_line_item.get(db, line_item_id)
        updated = crud_quote_line_item.update(db, db_obj, obj_in)

        quote = crud_quote.get(db, updated.quote_id)
        self._recalculate(db, quote)

        audit_log_service.log(
            db, "quote_line_item_updated", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Updated {updated.service_name or updated.part_name} to x{updated.quantity} on Quote #{quote.quote_number}",
        )

        return updated

    def remove_line_item(self, db: Session, line_item_id: int, current_user_id: int):
        db_obj = crud_quote_line_item.get(db, line_item_id)
        if not db_obj:
            return

        quote_id = db_obj.quote_id
        item_name = db_obj.service_name or db_obj.part_name

        crud_quote_line_item.delete(db, line_item_id)

        quote = crud_quote.get(db, quote_id)
        self._recalculate(db, quote)

        audit_log_service.log(
            db, "quote_line_item_removed", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Removed {item_name} from Quote #{quote.quote_number}",
        )

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Deletes a quote outright -- the one exception to quotes/invoices
        otherwise never being deletable. Only permitted for an accidental,
        never-touched quote: no line items yet, never emailed, never
        converted to an invoice, and only if it's the most recently
        issued quote number -- deleting anything but the latest would
        leave a permanent gap in the sequence, which is exactly what
        the independent, sequential numbering exists to avoid.

        Raises:
            HTTPException: 404 if the quote doesn't exist. 400 if it
                fails any of the conditions above.
        """
        quote = crud_quote.get(db, id)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")

        if crud_quote_line_item.get_by_quote(db, id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This quote has line items and can't be deleted.")
        if quote.quote_sent_at is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This quote has already been sent and can't be deleted.")
        if quote.converted_invoice_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This quote has already been converted to an invoice and can't be deleted.")

        most_recent_number = db.query(func.max(Quote.quote_number)).scalar()
        if quote.quote_number != most_recent_number:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only the most recently created quote can be deleted, to avoid leaving a gap in the numbering.")

        audit_log_service.log(
            db, "quote_deleted", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Deleted unsent, empty Quote #{quote.quote_number}",
        )
        crud_quote.delete(db, quote)

    # -----------------------------------------------------------------
    # Conversion to Invoice
    # -----------------------------------------------------------------
    def convert_to_invoice(self, db: Session, quote_id: int, current_user_id: int):
        """
        Converts an approved quote into a real Invoice -- copies every
        line item (already-frozen snapshots, carried over exactly, not
        re-snapshotted) and the discount/tax selection, then links the
        quote to the new invoice it became.

        Raises:
            HTTPException: 404 if the quote doesn't exist. 400 if this
                quote has already been converted -- converting twice
                would create a duplicate invoice for the same work.
        """
        quote = crud_quote.get(db, quote_id)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
        if quote.converted_invoice_id is not None:
            existing_invoice = crud_invoice.get(db, quote.converted_invoice_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This quote was already converted to Invoice #{existing_invoice.invoice_number if existing_invoice else quote.converted_invoice_id}.",
            )

        next_invoice_number = (db.query(func.max(Invoice.invoice_number)).scalar() or 0) + 1
        new_invoice = Invoice(
            ticket_id=quote.ticket_id,
            discount_id=quote.discount_id,
            tax_rate_id=quote.tax_rate_id,
            details=quote.details,
            invoice_number=next_invoice_number,
        )
        db.add(new_invoice)
        db.commit()
        db.refresh(new_invoice)
        new_invoice.subtotal = quote.subtotal
        new_invoice.discount_name = quote.discount_name
        new_invoice.discount_amount = quote.discount_amount
        new_invoice.tax_rate_name = quote.tax_rate_name
        new_invoice.tax_amount = quote.tax_amount
        new_invoice.total = quote.total
        new_invoice.source_quote_id = quote.id
        db.commit()
        db.refresh(new_invoice)

        for quote_line_item in crud_quote_line_item.get_by_quote(db, quote_id):
            crud_invoice_line_item.create(
                db, new_invoice.id, quote_line_item.quantity, quote_line_item.unit_price,
                service_id=quote_line_item.service_id, service_name=quote_line_item.service_name,
                part_id=quote_line_item.part_id, part_name=quote_line_item.part_name,
            )
            if quote_line_item.part_id is not None:
                part_service.deduct_stock(db, quote_line_item.part_id, quote_line_item.quantity)

        quote.converted_invoice_id = new_invoice.id
        db.commit()

        audit_log_service.log(
            db, "quote_converted_to_invoice", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Quote #{quote.quote_number} converted to Invoice #{new_invoice.invoice_number}",
        )

        return new_invoice

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _next_quote_number(self, db: Session) -> int:
        """
        Returns:
            The next quote_number to assign: the current highest plus
            one, or 1 if there are no quotes at all. This correctly
            reuses a freed number without needing a full gap search,
            because delete() only ever permits deleting the single
            most-recently-numbered quote -- a number can only ever go
            missing at the very top of the sequence, never in the
            middle, so max()+1 is always the same as "the lowest
            genuinely available number."
        """
        current_max = db.query(func.max(Quote.quote_number)).scalar()
        return (current_max or 0) + 1

    def _recalculate(self, db: Session, quote):
        line_items = crud_quote_line_item.get_by_quote(db, quote.id)
        discount = crud_discount.get(db, quote.discount_id) if quote.discount_id else None
        tax_rate = crud_tax_rate.get(db, quote.tax_rate_id) if quote.tax_rate_id else None

        totals = calculate_totals(
            line_items,
            discount.percentage if discount else None,
            tax_rate.percentage if tax_rate else None,
        )

        quote.subtotal = totals["subtotal"]
        quote.discount_amount = totals["discount_amount"]
        quote.tax_amount = totals["tax_amount"]
        quote.total = totals["total"]
        db.commit()
        db.refresh(quote)

    def _snapshot_discount_and_tax_names(self, db: Session, quote):
        """Called whenever discount_id or tax_rate_id might have changed."""
        discount = crud_discount.get(db, quote.discount_id) if quote.discount_id else None
        tax_rate = crud_tax_rate.get(db, quote.tax_rate_id) if quote.tax_rate_id else None
        quote.discount_name = discount.name if discount else None
        quote.tax_rate_name = tax_rate.name if tax_rate else None
        db.commit()
        db.refresh(quote)

quote_service = QuoteService()
