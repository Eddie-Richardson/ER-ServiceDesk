# ER-ServiceDesk/app/routes/note_templates.py
"""
REST endpoints for a reusable template for a ticket's notes, whether internal or emailed to the customer.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.note_template_service import note_template_service
from app.schemas.note_template import NoteTemplate, NoteTemplateCreate, NoteTemplateUpdate

router = APIRouter(prefix="/note_templates", tags=["note_templates"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[NoteTemplate])
def list_note_templates(db: Session = Depends(get_db)):
    return note_template_service.get_multi(db)

@router.get("/{id}", response_model=NoteTemplate)
def get_note_template(id: int, db: Session = Depends(get_db)):
    return note_template_service.get(db, id)

@router.post("/", response_model=NoteTemplate)
def create_note_template(obj_in: NoteTemplateCreate, db: Session = Depends(get_db)):
    return note_template_service.create(db, obj_in)

@router.put("/{id}", response_model=NoteTemplate)
def update_note_template(id: int, obj_in: NoteTemplateUpdate, db: Session = Depends(get_db)):
    return note_template_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_note_template(id: int, db: Session = Depends(get_db)):
    return note_template_service.delete(db, id)
