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
from app.models.ticket_status import TicketStatus
from app.models.ticket_category import TicketCategory
from app.models.ticket_type import TicketType
from app.models.location import Location
from app.models.ticket_stage import TicketStage
from app.models.ticket_type_stage import TicketTypeStage

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

    # -------------------------------------------------------------------
    # Ticket statuses (high-level workflow state)
    # -------------------------------------------------------------------
    statuses = [
        ("Open", "#3B82F6", "Newly created, not yet started"),
        ("In Progress", "#F59E0B", "Actively being worked on"),
        ("Waiting on Parts", "#A855F7", "Blocked pending a parts order"),
        ("Waiting on Customer", "#6B7280", "Blocked pending customer response"),
        ("Resolved", "#10B981", "Work complete, pending pickup/close"),
        ("Closed", "#374151", "Ticket fully closed"),
    ]
    status_objs = {}
    for name, color, desc in statuses:
        existing = db.query(TicketStatus).filter_by(name=name).first()
        if existing:
            status_objs[name] = existing
        else:
            obj = TicketStatus(name=name, color=color, description=desc)
            db.add(obj)
            status_objs[name] = obj
    db.commit()

    # -------------------------------------------------------------------
    # Ticket categories (high-level grouping)
    # -------------------------------------------------------------------
    categories = [
        ("Hardware", "Physical component issues"),
        ("Software", "OS, driver, or application issues"),
        ("Network", "Connectivity and networking issues"),
        ("Custom Build", "New PC build from customer spec"),
    ]
    for name, desc in categories:
        if not db.query(TicketCategory).filter_by(name=name).first():
            db.add(TicketCategory(name=name, description=desc))
    db.commit()

    # -------------------------------------------------------------------
    # Ticket types -- drives which stages are valid, via TicketTypeStage
    # -------------------------------------------------------------------
    types = [
        ("Repair", "Diagnose and fix an existing customer device"),
        ("Custom Build", "Assemble a new PC from a customer order"),
    ]
    type_objs = {}
    for name, desc in types:
        existing = db.query(TicketType).filter_by(name=name).first()
        if existing:
            type_objs[name] = existing
        else:
            obj = TicketType(name=name, description=desc)
            db.add(obj)
            type_objs[name] = obj
    db.commit()

    # -------------------------------------------------------------------
    # Locations (where a device/asset/part physically is)
    # -------------------------------------------------------------------
    locations = [
        ("Front Desk", "Customer intake/pickup counter"),
        ("Bench 1", "Repair workbench 1"),
        ("Bench 2", "Repair workbench 2"),
        ("Parts Shelf", "Parts storage"),
        ("Shipping/Receiving", "Inbound/outbound shipping area"),
        ("Customer Pickup Shelf", "Completed jobs awaiting pickup"),
    ]
    for name, desc in locations:
        if not db.query(Location).filter_by(name=name).first():
            db.add(Location(name=name, description=desc))
    db.commit()

    # -------------------------------------------------------------------
    # Ticket stages (granular step of work, restricted per type below)
    # -------------------------------------------------------------------
    repair_stages = [
        ("Diagnosing", "Identifying the cause of the issue"),
        ("Awaiting Parts", "Waiting on a parts order to arrive"),
        ("In Repair", "Actively repairing the device"),
        ("Testing", "Verifying the fix"),
        ("Ready for Pickup", "Repair complete, awaiting customer pickup"),
    ]
    build_stages = [
        ("Awaiting Parts", "Waiting on a parts order to arrive"),
        ("Assembling", "Physically assembling the build"),
        ("OS Install", "Installing and configuring the operating system"),
        ("Burn-in Test", "Stress-testing the build for stability"),
        ("QC", "Final quality check before handoff"),
        ("Ready for Pickup", "Build complete, awaiting customer pickup"),
    ]

    stage_objs = {}
    for name, desc in repair_stages + build_stages:
        if name not in stage_objs:
            existing = db.query(TicketStage).filter_by(name=name).first()
            stage_objs[name] = existing or TicketStage(name=name, description=desc)
            if not existing:
                db.add(stage_objs[name])
    db.commit()

    # -------------------------------------------------------------------
    # Restrict stages per type via the TicketTypeStage allow-list
    # -------------------------------------------------------------------
    def allow(type_name, stage_name):
        """Add (type, stage) to the allow-list if not already present."""
        type_obj = type_objs[type_name]
        stage_obj = stage_objs[stage_name]
        exists = (
            db.query(TicketTypeStage)
            .filter_by(type_id=type_obj.id, stage_id=stage_obj.id)
            .first()
        )
        if not exists:
            db.add(TicketTypeStage(type_id=type_obj.id, stage_id=stage_obj.id))

    for name, _ in repair_stages:
        allow("Repair", name)
    for name, _ in build_stages:
        allow("Custom Build", name)

    db.commit()

    print("Seed data inserted successfully.")
