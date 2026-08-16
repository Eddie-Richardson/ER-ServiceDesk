# ER-ServiceDesk/app/services/quote_service.py
# Service layer for Quote.
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
from sqlalchemy.orm import Session

from app.crud.quote import crud_quote
from app.crud.quote_line_item import crud_quote_line_item
from app.crud.service import crud_service
from app.crud.part import crud_part
from app.crud.discount import crud_discount
from app.crud.tax_rate import crud_tax_rate
from app.crud.invoice import crud_invoice
from app.crud.invoice_line_item import crud_invoice_line_item
from app.schemas.quote import QuoteCreate, QuoteUpdate
from app.schemas.quote_line_item import QuoteLineItemUpdate
from app.schemas.invoice import InvoiceCreate
from app.services.billing_calculations import calculate_totals
from app.services.audit_log_service import audit_log_service


class QuoteService:
    """Business logic for Quote operations, including line items and conversion to an Invoice."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Quote by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Quote instance, or None if not found.
        """
        return crud_quote.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Quote records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Quote instances.
        """
        return crud_quote.get_multi(db, skip, limit)

    def get_by_ticket(self, db: Session, ticket_id: int):
        """
        Fetch every quote for a given ticket.

        Args:
            db: Active database session.
            ticket_id: The ticket to look up quotes for.

        Returns:
            A list of Quote instances for that ticket.
        """
        return crud_quote.get_by_ticket(db, ticket_id)

    def create(self, db: Session, obj_in: QuoteCreate, current_user_id: int):
        """
        Create a new Quote. Starts with zero line items and zero
        totals -- add_line_item() builds it up from there.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.
            current_user_id: The user creating this quote -- recorded
                in the audit trail.

        Returns:
            The newly created Quote instance.
        """
        new_quote = crud_quote.create(db, obj_in)
        self._snapshot_discount_and_tax_names(db, new_quote)

        audit_log_service.log(
            db, "quote_created", "ticket", new_quote.ticket_id, user_id=current_user_id,
            details=f"Quote #{new_quote.id} created",
        )

        return new_quote

    def update(self, db: Session, id: int, obj_in: QuoteUpdate, current_user_id: int):
        """
        Update an existing Quote's discount/tax selection or details.
        Changing discount_id or tax_rate_id triggers a full totals
        recalculation.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated Quote instance.
        """
        db_obj = crud_quote.get(db, id)
        updated = crud_quote.update(db, db_obj, obj_in)
        self._snapshot_discount_and_tax_names(db, updated)
        self._recalculate(db, updated)

        audit_log_service.log(
            db, "quote_updated", "ticket", updated.ticket_id, user_id=current_user_id,
            details=f"Quote #{updated.id} updated",
        )

        return updated

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Delete a Quote by ID. Its own line items are cascade-deleted
        with it (see Quote.line_items' own cascade setting) -- they're
        a structural detail of this quote, not an independent record.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
            current_user_id: The user performing this deletion --
                recorded in the audit trail.
        """
        db_obj = crud_quote.get(db, id)
        ticket_id = db_obj.ticket_id if db_obj else None

        result = crud_quote.delete(db, id)

        if ticket_id is not None:
            audit_log_service.log(
                db, "quote_deleted", "ticket", ticket_id, user_id=current_user_id,
                details=f"Quote #{id} deleted",
            )

        return result

    # -----------------------------------------------------------------
    # Line items
    # -----------------------------------------------------------------
    def add_line_item(self, db: Session, quote_id: int, quantity: int, current_user_id: int, service_id: int | None = None, part_id: int | None = None):
        """
        Adds a new line item to a quote -- either a service or a real
        inventory part, snapshotting its current name and price, then
        recalculates totals. Never touches inventory -- a quote isn't
        a real transaction yet; see invoice_service.add_line_item()
        for where part deduction actually happens.

        Args:
            db: Active database session.
            quote_id: The quote to add this line item to.
            quantity: How many units.
            current_user_id: The user adding this line item -- recorded
                in the audit trail.
            service_id: The service being added, if this is a service line.
            part_id: The part being added, if this is a part line.

        Returns:
            The newly created QuoteLineItem instance.

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
            details=f"Added {item_name} x{quantity} (${item_price}) to Quote #{quote_id}",
        )

        return line_item

        return line_item

    def update_line_item(self, db: Session, line_item_id: int, obj_in: QuoteLineItemUpdate, current_user_id: int):
        """
        Updates a line item's quantity, then recalculates totals.

        Args:
            db: Active database session.
            line_item_id: The line item to update.
            obj_in: Fields to change (only quantity is editable).
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated QuoteLineItem instance.
        """
        db_obj = crud_quote_line_item.get(db, line_item_id)
        updated = crud_quote_line_item.update(db, db_obj, obj_in)

        quote = crud_quote.get(db, updated.quote_id)
        self._recalculate(db, quote)

        audit_log_service.log(
            db, "quote_line_item_updated", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Updated {updated.service_name or updated.part_name} to x{updated.quantity} on Quote #{updated.quote_id}",
        )

        return updated

    def remove_line_item(self, db: Session, line_item_id: int, current_user_id: int):
        """
        Removes a line item from a quote, then recalculates totals.

        Args:
            db: Active database session.
            line_item_id: The line item to remove.
            current_user_id: The user removing this line item --
                recorded in the audit trail.
        """
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
            details=f"Removed {item_name} from Quote #{quote_id}",
        )

    # -----------------------------------------------------------------
    # Conversion to Invoice
    # -----------------------------------------------------------------
    def convert_to_invoice(self, db: Session, quote_id: int, current_user_id: int):
        """
        Converts an approved quote into a real Invoice -- copies every
        line item (already-frozen snapshots, carried over exactly, not
        re-snapshotted) and the discount/tax selection, then links the
        quote to the new invoice it became.

        Args:
            db: Active database session.
            quote_id: The quote to convert.
            current_user_id: The user performing this conversion --
                recorded in the audit trail.

        Returns:
            The newly created Invoice instance.

        Raises:
            HTTPException: 404 if the quote doesn't exist. 400 if this
                quote has already been converted -- converting twice
                would create a duplicate invoice for the same work.
        """
        quote = crud_quote.get(db, quote_id)
        if not quote:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quote not found")
        if quote.converted_invoice_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"This quote was already converted to Invoice #{quote.converted_invoice_id}.",
            )

        new_invoice = crud_invoice.create(db, InvoiceCreate(
            ticket_id=quote.ticket_id,
            discount_id=quote.discount_id,
            tax_rate_id=quote.tax_rate_id,
            details=quote.details,
        ))
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
                db, new_invoice.id, quote_line_item.service_id, quote_line_item.service_name,
                quote_line_item.quantity, quote_line_item.unit_price,
            )

        quote.converted_invoice_id = new_invoice.id
        db.commit()

        audit_log_service.log(
            db, "quote_converted_to_invoice", "ticket", quote.ticket_id, user_id=current_user_id,
            details=f"Quote #{quote_id} converted to Invoice #{new_invoice.id}",
        )

        return new_invoice

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _recalculate(self, db: Session, quote):
        """
        Recomputes and stores subtotal/discount_amount/tax_amount/total
        from this quote's current line items and discount/tax
        selection.

        Args:
            db: Active database session.
            quote: The Quote instance to recalculate (already loaded).
        """
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
        """
        Re-snapshots discount_name/tax_rate_name from the currently
        selected Discount/TaxRate -- called whenever discount_id or
        tax_rate_id might have changed.

        Args:
            db: Active database session.
            quote: The Quote instance to update (already loaded).
        """
        discount = crud_discount.get(db, quote.discount_id) if quote.discount_id else None
        tax_rate = crud_tax_rate.get(db, quote.tax_rate_id) if quote.tax_rate_id else None
        quote.discount_name = discount.name if discount else None
        quote.tax_rate_name = tax_rate.name if tax_rate else None
        db.commit()
        db.refresh(quote)

quote_service = QuoteService()
