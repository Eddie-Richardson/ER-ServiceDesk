# ER-ServiceDesk/tests/test_record_lock.py
"""
Covers RecordLockService -- acquire/release, re-acquiring your own
lock, a second user genuinely blocked by an active lock (with a real
409 naming who holds it), releasing a lock you don't hold as a safe
no-op, a stale (abandoned) lock being reclaimable after the timeout,
and that the timeout itself is genuinely configurable via
SystemSetting rather than hardcoded.
"""

from tests.factories import make_plain_user

def _headers_for_user(user):
    """Builds an Authorization header for an arbitrary already-created user, for tests that need two distinct authenticated users."""
    from app.core.security import create_access_token
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_lock_acquire_and_release(client, agent_headers):
    acquire_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 1}, headers=agent_headers)
    assert acquire_resp.status_code == 200, acquire_resp.text

    release_resp = client.post("/locks/release", json={"entity_type": "ticket", "entity_id": 1}, headers=agent_headers)
    assert release_resp.status_code == 200
    assert release_resp.json()["released"] is True


def test_lock_same_user_can_reacquire_their_own_lock(client, agent_headers):
    """Re-opening the same record you already have locked succeeds, rather than treating yourself as a conflict."""
    first_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 2}, headers=agent_headers)
    assert first_resp.status_code == 200

    second_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 2}, headers=agent_headers)
    assert second_resp.status_code == 200


def test_lock_different_user_blocked_by_active_lock(client, agent_headers, db):
    """A second user trying to acquire a lock someone else already holds gets a 409 naming who holds it."""
    other_user = make_plain_user(db, email="other_locker@example.com")
    other_headers = _headers_for_user(other_user)

    first_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 3}, headers=agent_headers)
    assert first_resp.status_code == 200

    conflict_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 3}, headers=other_headers)
    assert conflict_resp.status_code == 409
    assert "Currently being edited by" in conflict_resp.json()["error"]["message"]


def test_lock_release_by_non_holder_is_a_safe_no_op(client, agent_headers, db):
    """Releasing a lock you don't hold doesn't error and doesn't affect the actual holder's lock."""
    other_user = make_plain_user(db, email="non_holder@example.com")
    other_headers = _headers_for_user(other_user)

    acquire_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 4}, headers=agent_headers)
    assert acquire_resp.status_code == 200

    release_resp = client.post("/locks/release", json={"entity_type": "ticket", "entity_id": 4}, headers=other_headers)
    assert release_resp.status_code == 200

    still_conflicts_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 4}, headers=other_headers)
    assert still_conflicts_resp.status_code == 409


def test_lock_release_of_never_locked_record_is_a_safe_no_op(client, agent_headers):
    resp = client.post("/locks/release", json={"entity_type": "ticket", "entity_id": 999}, headers=agent_headers)
    assert resp.status_code == 200
    assert resp.json()["released"] is True


def test_lock_stale_lock_can_be_reclaimed_by_another_user(client, agent_headers, db):
    """A lock older than lock_timeout_minutes (default 15) is treated as abandoned and can be reclaimed by someone else, covering the case where the original holder's app crashed without releasing it."""
    from datetime import datetime, timedelta, timezone
    from app.models.record_lock import RecordLock

    other_user = make_plain_user(db, email="reclaimer@example.com")
    other_headers = _headers_for_user(other_user)

    acquire_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 5}, headers=agent_headers)
    assert acquire_resp.status_code == 200
    stale_lock = db.query(RecordLock).filter_by(entity_type="ticket", entity_id=5).first()
    stale_lock.locked_at = datetime.now(timezone.utc) - timedelta(minutes=20)
    db.commit()

    reclaim_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 5}, headers=other_headers)
    assert reclaim_resp.status_code == 200, reclaim_resp.text


def test_lock_timeout_is_configurable_via_system_setting(client, agent_headers, superuser_headers, db):
    """A custom, shorter lock_timeout_minutes setting is genuinely honored, not just the hardcoded 15-minute default."""
    from datetime import datetime, timedelta, timezone
    from app.models.record_lock import RecordLock

    custom_timeout_resp = client.put("/system_settings/by-key/lock_timeout_minutes", json={"value": "5"}, headers=superuser_headers)
    assert custom_timeout_resp.status_code == 200, custom_timeout_resp.text

    other_user = make_plain_user(db, email="short_timeout_reclaimer@example.com")
    other_headers = _headers_for_user(other_user)

    acquire_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 6}, headers=agent_headers)
    assert acquire_resp.status_code == 200

    lock = db.query(RecordLock).filter_by(entity_type="ticket", entity_id=6).first()
    lock.locked_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    db.commit()

    reclaim_resp = client.post("/locks/acquire", json={"entity_type": "ticket", "entity_id": 6}, headers=other_headers)
    assert reclaim_resp.status_code == 200, reclaim_resp.text


