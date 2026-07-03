# ER-ServiceDesk/app/routes/auth.py
# Authentication routes.
"""
Public-facing authentication endpoint(s).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.auth_service import auth_service
from app.schemas.user import UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and issue an access token.

    Args:
        credentials: Submitted email and password.
        db: Injected database session.

    Returns:
        A dict with `access_token` and `token_type`.

    Raises:
        HTTPException: 400 if the credentials are invalid.
    """
    user = auth_service.authenticate(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    return auth_service.login(user)
