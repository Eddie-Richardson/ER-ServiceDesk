# ER-ServiceDesk/app/routes/auth.py
# Authentication routes.
"""
Public-facing authentication endpoint(s).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import get_db
from app.services.auth_service import auth_service
from app.schemas.user import ChangePasswordRequest, UserLogin

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate a user and issue an access token.

    If the account's password was set by an admin (a new account, or
    a Reset Password action) rather than chosen by the user, no token
    is issued -- the credentials were valid, but the account must go
    through POST /auth/change-password before it can do anything else.
    This is the enforcement point for that requirement: a client can't
    work around it by simply ignoring a client-side flag, since there's
    no token to make an authenticated request with until the password
    is actually changed.

    Args:
        credentials: Submitted email and password.
        db: Injected database session.

    Returns:
        Normally, a dict with `access_token` and `token_type`. If a
        password change is required first, instead a dict with
        `must_change_password: true` and no token.

    Raises:
        HTTPException: 400 if the credentials are invalid.
    """
    user = auth_service.authenticate(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if user.must_change_password:
        return {"must_change_password": True}

    return auth_service.login(db, user)


@router.post("/change-password")
def change_password(request: ChangePasswordRequest, db: Session = Depends(get_db)):
    """
    Self-service password change. Deliberately reachable without a
    normal access token -- its whole purpose is letting someone whose
    login was blocked by must_change_password (and who therefore has no
    token) set their own password. Re-verifies current_password itself
    rather than trusting anything the client claims, exactly like login.

    On success, clears must_change_password and returns a normal login
    token, so the person ends up signed in immediately rather than
    needing to log in a second time right after changing their password.

    Args:
        request: email, current_password (re-verified here), and the
            new password to set.
        db: Injected database session.

    Returns:
        A dict with `access_token` and `token_type`, same shape as a
        normal login.

    Raises:
        HTTPException: 400 if current_password is wrong, or if
            new_password fails length validation (too short, or over
            bcrypt's byte limit).
    """
    user = auth_service.authenticate(db, request.email, request.current_password)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    try:
        new_hash = hash_password(request.new_password)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    user.hashed_password = new_hash
    user.must_change_password = False
    db.commit()

    return auth_service.login(db, user)
