# ER-ServiceDesk/app/routes/business_info.py
# API route for fetching the shop's configured display name.
"""
Authenticated endpoint for a Client machine to fetch and cache the
shop's display name locally.

Requires a valid session -- no unauthenticated route exists for this
at all, deliberately. This does mean a Client's very first-ever login
screen (before any login has ever succeeded on that machine) won't
show this branding yet; it's cached locally the moment the first
login succeeds (see desktop/login_window.py), and every launch after
that shows it correctly. Local and Server installs read this the same
way too, now that business_name lives in the database (a real
SystemSetting, edited through Settings -> Business Info) rather than
being written to the Windows registry at install time.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.system_setting_service import system_setting_service

router = APIRouter(prefix="/business-info", tags=["business-info"], dependencies=[Depends(get_current_user)])


@router.get("/business-name")
def get_business_name(db: Session = Depends(get_db)):
    """
    Returns the shop's configured display name, or an empty string if
    never set.

    Returns:
        {"business_name": "..."}
    """
    return {"business_name": system_setting_service.get_str(db, "business_name", "")}
