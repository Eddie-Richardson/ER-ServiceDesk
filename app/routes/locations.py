# ER-ServiceDesk/app/routes/locations.py
# API routes for Location operations.
"""
REST endpoints for Location records.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.location_service import location_service
from app.schemas.location import Location, LocationCreate, LocationUpdate

router = APIRouter(prefix="/inventory/locations", tags=["inventory-locations"])

@router.get("/", response_model=list[Location])
def list_locations(db: Session = Depends(get_db)):
    """List Location records, paginated."""
    return location_service.get_multi(db)

@router.get("/{{id}}", response_model=Location)
def get_location(id: int, db: Session = Depends(get_db)):
    """Fetch a single Location record by ID."""
    return location_service.get(db, id)

@router.post("/", response_model=Location)
def create_location(obj_in: LocationCreate, db: Session = Depends(get_db)):
    """Create a new Location record."""
    return location_service.create(db, obj_in)

@router.put("/{{id}}", response_model=Location)
def update_location(id: int, obj_in: LocationUpdate, db: Session = Depends(get_db)):
    """Update an existing Location record."""
    return location_service.update(db, id, obj_in)

@router.delete("/{{id}}")
def delete_location(id: int, db: Session = Depends(get_db)):
    """Delete a Location record by ID."""
    return location_service.delete(db, id)
