# ER-ServiceDesk/app/services/record_lock_service.py
# Service layer for check-out style record locking.

"""
Business logic for acquiring and releasing record locks.

A lock is considered abandoned (and safely reclaimable) once it's older
than LOCK_TIMEOUT_MINUTES -- checked lazily, whenever someone next tries
to acquire it, rather than via a separate scheduled cleanup job. This
covers the case a check-out lock always has to answer for: what happens
if the person holding it closes their laptop, loses power, or their app
crashes without releasing it. Nobody else should be locked out forever
because of that.
"""

from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.record_lock import RecordLock

LOCK_TIMEOUT_MINUTES = 15


class RecordLockService:
    """Business logic for the check-out style record locking system."""

    def acquire(self, db: Session, entity_type: str, entity_id: int, user_id: int) -> RecordLock:
        """
        Attempts to acquire a lock on a record for the given user.

        Succeeds if the record is unlocked, already locked by this same
        user (e.g. they re-opened it), or the existing lock has gone
        stale past LOCK_TIMEOUT_MINUTES with no one having released it.

        Args:
            db: Active database session.
            entity_type: The kind of record being locked, e.g. "ticket".
            entity_id: The record's own primary key.
            user_id: The user attempting to acquire the lock.

        Returns:
            The new (or refreshed) RecordLock.

        Raises:
            HTTPException: 409 if someone else currently holds a
                non-stale lock on this record. The error detail names
                who holds it and when they acquired it, so the client
                can show a clear message.
        """
        existing = (
            db.query(RecordLock)
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .first()
        )

        if existing:
            is_same_user = existing.locked_by_user_id == user_id
            locked_at = existing.locked_at
            if locked_at.tzinfo is None:
                # Defensive: some DB drivers round-trip a "timezone aware"
                # column as a naive datetime. Every lock is always
                # stored in UTC (see the column's default above), so a
                # naive value can be safely assumed to already be UTC
                # rather than raising on the comparison below.
                locked_at = locked_at.replace(tzinfo=timezone.utc)
            is_stale = (
                datetime.now(timezone.utc) - locked_at
                > timedelta(minutes=LOCK_TIMEOUT_MINUTES)
            )
            if not is_same_user and not is_stale:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Currently being edited by {existing.locked_by.full_name}.",
                )
            # Either the same user is re-acquiring, or the previous
            # lock was abandoned -- clear it and issue a fresh one below.
            db.delete(existing)
            db.commit()

        new_lock = RecordLock(entity_type=entity_type, entity_id=entity_id, locked_by_user_id=user_id)
        db.add(new_lock)
        db.commit()
        db.refresh(new_lock)
        return new_lock

    def release(self, db: Session, entity_type: str, entity_id: int, user_id: int):
        """
        Releases a lock, if the given user is the one currently holding it.

        A safe no-op if the record isn't locked at all, or is locked by
        someone else -- callers only ever release their own locks (on
        closing a dialog), so there's no legitimate case where this
        should raise for either of those situations.

        Args:
            db: Active database session.
            entity_type: The kind of record, e.g. "ticket".
            entity_id: The record's own primary key.
            user_id: The user releasing the lock.
        """
        existing = (
            db.query(RecordLock)
            .filter_by(entity_type=entity_type, entity_id=entity_id)
            .first()
        )
        if existing and existing.locked_by_user_id == user_id:
            db.delete(existing)
            db.commit()


record_lock_service = RecordLockService()
