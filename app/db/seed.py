# ER-ServiceDesk/app/db/seed.py
# Seed initial system data
"""
Populates a fresh database with baseline roles, permissions,
role-permission mappings, and default users so the system is immediately
usable after migrations run. Idempotent -- safe to run multiple times.
"""

from sqlalchemy.orm import Session

from app.models.role import Role
from app.models.permission import Permission
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole

from app.core.security import hash_password


def seed_data(db: Session):
    """
    Insert initial roles, permissions, mappings, and default users.

    Existing entries are detected and reused rather than duplicated, so
    this is safe to call on every startup/deploy.

    Args:
        db: Active database session.
    """

    # -------------------------------------------------------------------
    # Roles
    # -------------------------------------------------------------------
    roles = {
        "admin": "System administrator with full access",
        "agent": "Technician/employee with operational access",
    }

    role_objs = {}
    for name, desc in roles.items():
        existing = db.query(Role).filter_by(name=name).first()
        if existing:
            role_objs[name] = existing
        else:
            role = Role(name=name, description=desc)
            db.add(role)
            role_objs[name] = role

    db.commit()

    # -------------------------------------------------------------------
    # Permissions
    # -------------------------------------------------------------------
    permissions = [
        ("ticket.create", "Create new tickets"),
        ("ticket.update", "Update ticket details"),
        ("ticket.status", "Change ticket status"),
        ("ticket.assign", "Assign tickets to agents"),
        ("ticket.view_all", "View all tickets"),
        ("comment.add", "Add comments to tickets"),
        ("note.add_internal", "Add internal technician notes"),
        ("attachment.add", "Upload attachments"),
        ("user.manage", "Manage system users"),
        ("role.manage", "Manage roles and permissions"),
        ("audit.view", "View audit logs"),
    ]

    perm_objs = {}
    for name, desc in permissions:
        existing = db.query(Permission).filter_by(name=name).first()
        if existing:
            perm_objs[name] = existing
        else:
            perm = Permission(name=name, description=desc)
            db.add(perm)
            perm_objs[name] = perm

    db.commit()

    # -------------------------------------------------------------------
    # Role -> Permission mapping
    # -------------------------------------------------------------------
    admin_perms = permissions
    agent_perms = [
        p for p in permissions
        if p[0] not in ("user.manage", "role.manage", "audit.view")
    ]

    def assign_perms(role_name, perm_list):
        """Grant every permission in perm_list to the given role, skipping duplicates."""
        role = role_objs[role_name]
        for perm_name, _ in perm_list:
            perm = perm_objs[perm_name]

            exists = (
                db.query(RolePermission)
                .filter_by(role_id=role.id, permission_id=perm.id)
                .first()
            )
            if not exists:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    assign_perms("admin", admin_perms)
    assign_perms("agent", agent_perms)

    db.commit()

    # -------------------------------------------------------------------
    # Default admin user
    # -------------------------------------------------------------------
    admin_email = "admin@example.com"
    admin_user = db.query(User).filter_by(email=admin_email).first()

    if not admin_user:
        admin_user = User(
            email=admin_email,
            hashed_password=hash_password("admin123"),
            first_name="Admin",
            last_name="User",
            is_active=True,
            is_superuser=True,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        db.add(UserRole(user_id=admin_user.id, role_id=role_objs["admin"].id))

    db.commit()

    # -------------------------------------------------------------------
    # Default agent user
    # -------------------------------------------------------------------
    agent_email = "agent@example.com"
    agent_user = db.query(User).filter_by(email=agent_email).first()

    if not agent_user:
        agent_user = User(
            email=agent_email,
            hashed_password=hash_password("agent123"),
            first_name="Agent",
            last_name="User",
            is_active=True,
            is_superuser=False,
        )
        db.add(agent_user)
        db.commit()
        db.refresh(agent_user)

        db.add(UserRole(user_id=agent_user.id, role_id=role_objs["agent"].id))

    db.commit()

    print("Seed data inserted successfully.")
