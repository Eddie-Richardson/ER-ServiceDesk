# ER-ServiceDesk/app/services/note_template_service.py
"""
Business logic for a reusable template for a ticket's notes, whether internal or emailed to the customer.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.note_template import crud_note_template
from app.schemas.note_template import NoteTemplateCreate, NoteTemplateUpdate

class NoteTemplateService:
    """Business logic for NoteTemplate operations."""

    def get(self, db: Session, id: int):
        return crud_note_template.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_note_template.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: NoteTemplateCreate):
        return crud_note_template.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: NoteTemplateUpdate):
        db_obj = crud_note_template.get(db, id)
        return crud_note_template.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_note_template.delete(db, id)

note_template_service = NoteTemplateService()
