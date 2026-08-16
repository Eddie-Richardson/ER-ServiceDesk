# ER-ServiceDesk/app/services/user_service.py
# Service layer for User.
"""
Business logic for User accounts, including password hashing.

Handles password hashing on create/update, since the User model stores
`hashed_password` but the API schemas only ever accept/expose a plaintext
`password` field. This logic intentionally lives here (not in crud/user.py)
so the CRUD layer stays a generic, dumb data-access layer.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.crud.user import crud_user
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import generate_temp_password, hash_password
from app.core.email import send_email
from app.services.audit_log_service import audit_log_service

class UserService:
    """Business logic for User account operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single User by ID.

        Args:
            db: Active database session.
            id: Primary key of the user to fetch.

        Returns:
            The matching User instance, or None if not found.
        """
        return crud_user.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of User records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of User instances.
        """
        return crud_user.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: UserCreate, current_user_id: int):
        """
        Create a new User with a system-generated temporary password,
        emailed to the account's address before anything is written to
        the database.

        The admin never sees or chooses the real password -- only that
        it was generated and sent. The account is forced to change it
        on first login (must_change_password=True), which also blocks
        normal login until they do (see app.routes.auth).

        Args:
            db: Active database session.
            obj_in: Validated input data (no password field -- see
                UserCreate's docstring for why).
            current_user_id: The admin creating this account -- recorded
                in the audit trail.

        Returns:
            The newly created User instance.

        Raises:
            HTTPException: 400 if an account with this email already
                exists -- checked up front, before anything else
                happens, so a duplicate signup attempt fails cleanly
                without sending a confusing "your account was created"
                email to an address that already has one.
            HTTPException: 500 if the temp password email fails to
                send. The account is deliberately NOT created in this
                case -- an account whose password nobody actually
                received is worse than no account at all.
        """
        if crud_user.get_by_email(db, obj_in.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="An account with this email address already exists.",
            )

        temp_password = generate_temp_password()

        try:
            send_email(
                db=db,
                to_address=obj_in.email,
                subject="Your ER-ServiceDesk account",
                body=(
                    f"An account has been created for you.\n\n"
                    f"Email: {obj_in.email}\n"
                    f"Temporary password: {temp_password}\n\n"
                    f"You'll be asked to set your own password the first "
                    f"time you log in."
                ),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Couldn't send the account email, so the account was not created: {e}",
            )

        user_data = obj_in.model_dump()
        user_data["hashed_password"] = hash_password(temp_password)
        user_data["must_change_password"] = True

        db_obj = User(**user_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)

        audit_log_service.log(
            db, "user_created", "user", db_obj.id, user_id=current_user_id,
            details=f"Created account: {db_obj.email}",
        )

        return db_obj

    def reset_password(self, db: Session, id: int, current_user_id: int):
        """
        Generates a new temporary password for an existing user and
        emails it, following the same "email must succeed before
        anything changes" ordering as create(). Used for the Reset
        Password action in the Users & Roles window -- an admin never
        types or sees anyone's password directly, including their own
        resets of other accounts.

        Args:
            db: Active database session.
            id: The user whose password is being reset.
            current_user_id: The admin performing this reset --
                recorded in the audit trail.

        Returns:
            The updated User instance.

        Raises:
            HTTPException: 404 if the user doesn't exist, or 500 if the
                email fails to send -- in which case the password is
                deliberately left completely unchanged.
        """
        db_obj = crud_user.get(db, id)
        if not db_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        temp_password = generate_temp_password()

        try:
            send_email(
                db=db,
                to_address=db_obj.email,
                subject="Your ER-ServiceDesk password has been reset",
                body=(
                    f"Your password has been reset by an administrator.\n\n"
                    f"Temporary password: {temp_password}\n\n"
                    f"You'll be asked to set your own password the next "
                    f"time you log in."
                ),
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Couldn't send the reset email, so the password was not changed: {e}",
            )

        db_obj.hashed_password = hash_password(temp_password)
        db_obj.must_change_password = True
        db.commit()
        db.refresh(db_obj)

        audit_log_service.log(
            db, "user_password_reset", "user", db_obj.id, user_id=current_user_id,
            details=f"Password reset by administrator for: {db_obj.email}",
        )

        return db_obj

    def update(self, db: Session, id: int, obj_in: UserUpdate, current_user_id: int):
        """
        Update an existing User's non-password fields. Password changes
        never go through this method -- see reset_password() for
        admin-initiated resets, or POST /auth/change-password for
        self-service changes.

        Args:
            db: Active database session.
            id: Primary key of the user to update.
            obj_in: Fields to change; unset fields are left untouched.
            current_user_id: The admin making this change -- recorded
                in the audit trail.

        Returns:
            The updated User instance.

        Raises:
            HTTPException: 400 if the email is being changed to one
                already used by a DIFFERENT account -- same reasoning
                as create()'s own duplicate check, checked up front
                rather than left to an unhandled database constraint.
        """
        db_obj = crud_user.get(db, id)
        update_data = obj_in.model_dump(exclude_unset=True)

        if "email" in update_data and update_data["email"] != db_obj.email:
            existing = crud_user.get_by_email(db, update_data["email"])
            if existing and existing.id != id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="An account with this email address already exists.",
                )

        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        for field, value in update_data.items():
            setattr(db_obj, field, value)

        db.commit()
        db.refresh(db_obj)

        if changed_fields:
            audit_log_service.log(
                db, "user_updated", "user", db_obj.id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return db_obj

    def delete(self, db: Session, id: int, current_user_id: int):
        """
        Delete a User by ID.

        Args:
            db: Active database session.
            id: Primary key of the user to delete.
            current_user_id: The admin performing this deletion --
                recorded in the audit trail.
        """
        db_obj = crud_user.get(db, id)
        deleted_email = db_obj.email if db_obj else None

        result = crud_user.delete(db, id)

        audit_log_service.log(
            db, "user_deleted", "user", id, user_id=current_user_id,
            details=f"Deleted account: {deleted_email}" if deleted_email else None,
        )

        return result

user_service = UserService()
