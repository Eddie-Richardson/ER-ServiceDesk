# ER-ServiceDesk/app/routes/business_info_settings.py
"""
REST endpoints for managing the shop's business identity and email
configuration in full -- name, phone, the email account, and its
SMTP/IMAP settings. Superuser-only, same gating as
routes/system_settings.py -- this is meaningfully more sensitive than
that (it includes setting the email account's password), not less.

Deliberately separate from routes/business_info.py -- that one is a
narrow, any-logged-in-user endpoint for fetching just the display
name (used by Client machines to show correct branding). This one is
the real management screen behind Settings -> Business Info.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.business_info_service import business_info_service
from app.schemas.business_info import BusinessInfoOut, BusinessInfoUpdate

router = APIRouter(prefix="/business_info_settings", tags=["business_info_settings"], dependencies=[Depends(require_superuser)])


@router.get("/", response_model=BusinessInfoOut)
def get_business_info(db: Session = Depends(get_db)):
    """Fetch the shop's full business info. Never includes the actual email password, only whether one is set."""
    return business_info_service.get_full(db)


@router.put("/", response_model=BusinessInfoOut)
def update_business_info(obj_in: BusinessInfoUpdate, db: Session = Depends(get_db)):
    """Save the shop's business info. Leave email_password blank/omitted to keep the currently-stored password unchanged."""
    business_info_service.update(db, obj_in)
    return business_info_service.get_full(db)
