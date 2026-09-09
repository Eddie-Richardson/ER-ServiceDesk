# ER-ServiceDesk/tests/test_seed_data.py
"""
Covers app.db.seed.seed_data() -- the function that populates a fresh
database with baseline roles, permissions, and role-permission
mappings. Confirms it genuinely creates the expected data, is
genuinely idempotent (safe to call repeatedly, e.g. on every
deploy/startup), and -- the most security-relevant property -- creates
zero user accounts, since the only real way into a fresh install is
now the first-run admin screen (see test_first_run_admin.py).
"""

from app.db.seed import seed_data
from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User


def test_seed_data_creates_the_expected_roles(db):
    seed_data(db)
    role_names = {r.name for r in db.query(Role).all()}
    assert role_names == {"admin", "agent", "front_desk", "inventory_access", "billing_access"}


def test_seed_data_creates_the_expected_permissions(db):
    seed_data(db)
    perm_names = {p.name for p in db.query(Permission).all()}
    assert perm_names == {"tickets.manage", "customers.manage", "inventory.manage", "billing.manage"}


def test_seed_data_grants_agent_and_front_desk_identical_permissions(db):
    """Regression check for the deliberate design: agent and front_desk are distinct labels with identical real access."""
    seed_data(db)
    agent = db.query(Role).filter_by(name="agent").first()
    front_desk = db.query(Role).filter_by(name="front_desk").first()

    agent_perms = {rp.permission.name for rp in db.query(RolePermission).filter_by(role_id=agent.id).all()}
    front_desk_perms = {rp.permission.name for rp in db.query(RolePermission).filter_by(role_id=front_desk.id).all()}

    assert agent_perms == {"tickets.manage", "customers.manage"}
    assert front_desk_perms == {"tickets.manage", "customers.manage", "billing.manage"}


def test_seed_data_creates_zero_user_accounts(db):
    """The core security property: seed_data() must never create any default account -- the first-run admin screen is the only real way in."""
    seed_data(db)
    assert db.query(User).count() == 0


def test_seed_data_is_genuinely_idempotent(db):
    """Running seed_data() twice must not create duplicate roles/permissions/grants -- confirms it's genuinely safe to call on every startup/deploy, not just once."""
    seed_data(db)
    role_count_first = db.query(Role).count()
    perm_count_first = db.query(Permission).count()
    grant_count_first = db.query(RolePermission).count()

    seed_data(db)
    role_count_second = db.query(Role).count()
    perm_count_second = db.query(Permission).count()
    grant_count_second = db.query(RolePermission).count()

    assert role_count_first == role_count_second
    assert perm_count_first == perm_count_second
    assert grant_count_first == grant_count_second


def test_seed_data_removes_a_stale_permission_no_longer_in_the_canonical_list(db):
    """A leftover permission from a removed feature/old naming scheme gets cleaned up, along with any RolePermission rows pointing at it, rather than accumulating forever."""
    seed_data(db)

    stale = Permission(name="old_removed_feature.manage", description="No longer used")
    db.add(stale)
    db.commit()
    db.refresh(stale)

    admin_role = db.query(Role).filter_by(name="admin").first()
    stale_grant = RolePermission(role_id=admin_role.id, permission_id=stale.id)
    db.add(stale_grant)
    db.commit()

    seed_data(db)

    assert db.query(Permission).filter_by(name="old_removed_feature.manage").first() is None
    assert db.query(RolePermission).filter_by(permission_id=stale.id).first() is None
