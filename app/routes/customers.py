# ER-ServiceDesk/app/routes/customers.py
"""
REST endpoints for a client of the repair shop.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.customer_service import customer_service
from app.schemas.customer import Customer, CustomerCreate, CustomerUpdate

router = APIRouter(prefix="/customers", tags=["customers"], dependencies=[Depends(require_permission("customers.manage"))])

@router.get("/", response_model=list[Customer])
def list_customers(db: Session = Depends(get_db)):
    return customer_service.get_multi(db)

@router.get("/{id}", response_model=Customer)
def get_customer(id: int, db: Session = Depends(get_db)):
    return customer_service.get(db, id)

@router.post("/", response_model=Customer)
def create_customer(
    obj_in: CustomerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return customer_service.create(db, obj_in, current_user.id)

@router.put("/{id}", response_model=Customer)
def update_customer(
    id: int,
    obj_in: CustomerUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return customer_service.update(db, id, obj_in, current_user.id)

@router.delete("/{id}")
def delete_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return customer_service.delete(db, id, current_user.id)

@router.post("/{id}/archive", response_model=Customer)
def archive_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return customer_service.archive(db, id, current_user.id)

@router.post("/{id}/unarchive", response_model=Customer)
def unarchive_customer(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return customer_service.unarchive(db, id, current_user.id)
