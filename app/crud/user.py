# ER-ServiceDesk/app/crud/user.py
"""
Database access layer for User accounts.

create() takes hashed_password and must_change_password as explicit
parameters rather than fields on UserCreate, since both are genuinely
server-computed at creation time (a random temp password, hashed, and
forced on first login) -- never something a client submits directly.
See UserService.create() for where these are actually computed.

update() is intentionally NOT implemented here -- a password change
goes through UserService.reset_password() instead, which has its own
real business logic (re-sending the account email, etc.) beyond a
plain field update.
"""

from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.user import UserCreate

class UserCRUD:
    """Direct database access for User records."""

    def get(self, db: Session, id: int) -> User | None:
        return db.query(User).filter(User.id == id).first()

    def get_by_email(self, db: Session, email: str) -> User | None:
        """
        Used to check for a duplicate BEFORE attempting to create an
        account, so a signup attempt for an already-registered address
        fails cleanly up front instead of via an unhandled database
        constraint error later.
        """
        return db.query(User).filter(User.email == email).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(User).offset(skip).limit(limit).all()

    def any_exist(self, db: Session) -> bool:
        """
        Used by the first-run admin creation flow to decide whether
        any account exists at all yet -- if not, the desktop app shows
        a "Create your admin account" screen instead of the normal
        Login window (see users.py's first_run_router).
        """
        return db.query(User.id).first() is not None

    def create(self, db: Session, obj_in: UserCreate, hashed_password: str, must_change_password: bool) -> User:
        obj = User(**obj_in.model_dump(), hashed_password=hashed_password, must_change_password=must_change_password)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(User).filter(User.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_user = UserCRUD()
