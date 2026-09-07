# ER-ServiceDesk/app/crud/note.py
"""
Database access layer for a ticket's note/conversation history --
internal notes and customer-facing email exchange alike.
"""

from sqlalchemy.orm import Session
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate

class NoteCRUD:
    """Direct database access for Note records."""

    def get(self, db: Session, id: int) -> Note | None:
        return db.query(Note).filter(Note.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 500, ticket_id: int | None = None):
        query = db.query(Note)
        if ticket_id is not None:
            query = query.filter(Note.ticket_id == ticket_id)
        return query.order_by(Note.created_at).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: NoteCreate) -> Note:
        obj = Note(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Note, obj_in: NoteUpdate) -> Note:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Note).filter(Note.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_note = NoteCRUD()
