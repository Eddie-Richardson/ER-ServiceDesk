# ER-ServiceDesk/tests/test_audit_log_crud.py
"""
Covers AuditLogCRUD.get() and get_multi()'s three optional filter
parameters (user_id, entity_type, entity_id) directly at the
database-query level -- every existing test only ever calls
get_multi() unfiltered and filters the results in Python afterward,
never exercising these real SQL filter conditions themselves.
"""

from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogCreate
from tests.factories import make_plain_user


def _make_entry(db, action, entity_type, entity_id, user_id=None):
    return crud_audit_log.create(db, AuditLogCreate(action=action, entity_type=entity_type, entity_id=entity_id, user_id=user_id, details="test"))


def test_get_returns_the_real_record_by_id(db):
    entry = _make_entry(db, "test_action", "ticket", 1)
    result = crud_audit_log.get(db, entry.id)
    assert result.id == entry.id
    assert result.action == "test_action"


def test_get_returns_none_for_a_nonexistent_id(db):
    assert crud_audit_log.get(db, id=999999) is None


def test_get_multi_filters_by_user_id_at_the_database_level(db):
    user_a = make_plain_user(db, email="usera@example.com")
    user_b = make_plain_user(db, email="userb@example.com")
    _make_entry(db, "action_a", "ticket", 1, user_id=user_a.id)
    _make_entry(db, "action_b", "ticket", 2, user_id=user_b.id)

    result = crud_audit_log.get_multi(db, user_id=user_a.id)

    assert len(result) == 1
    assert result[0].user_id == user_a.id


def test_get_multi_filters_by_entity_type_at_the_database_level(db):
    _make_entry(db, "action_a", "ticket", 1)
    _make_entry(db, "action_b", "customer", 1)

    result = crud_audit_log.get_multi(db, entity_type="customer")

    assert len(result) == 1
    assert result[0].entity_type == "customer"


def test_get_multi_filters_by_entity_type_and_entity_id_together(db):
    """Both given together narrows to one specific entity instance -- e.g. a single ticket's own history, not every ticket's."""
    _make_entry(db, "action_a", "ticket", 1)
    _make_entry(db, "action_b", "ticket", 2)

    result = crud_audit_log.get_multi(db, entity_type="ticket", entity_id=1)

    assert len(result) == 1
    assert result[0].entity_id == 1


def test_audit_logs_is_read_only(client, superuser_headers):
    """AuditLog is a deliberately immutable, internally-generated record -- no create/update/delete route exists at all, only listing."""
    list_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert list_resp.status_code == 200
    create_resp = client.post("/audit_logs/", json={"action": "login", "entity_type": "user", "entity_id": 1}, headers=superuser_headers)
    assert create_resp.status_code == 405
