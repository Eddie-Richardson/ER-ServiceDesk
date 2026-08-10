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
from app.models.asset_category import AssetCategory
from app.models.ticket_stage import TicketStage
from app.models.ticket_type_stage import TicketTypeStage
from app.models.system_setting import SystemSetting

from app.core.security import hash_password


def seed_data(db: Session, business_name: str | None = None):
    """
    Insert initial roles, permissions, mappings, and default users.

    Existing entries are detected and reused rather than duplicated, so
    this is safe to call on every startup/deploy.

    Args:
        db: Active database session.
        business_name: The shop's display name, written to
            system_settings if provided and not already set. Only ever
            written once -- if an admin has already changed it via
            Settings, seeding again (e.g. after a container restart)
            must never silently overwrite that with whatever was in
            .env at first-run time.
    """

    # -------------------------------------------------------------------
    # Roles
    # -------------------------------------------------------------------
    # "admin" is cosmetic -- real admin access always comes from
    # User.is_superuser, a direct flag kept deliberately independent of
    # the Role system so it can't be lost as a side effect of role
    # bookkeeping. This role exists purely so an admin's profile shows
    # a label instead of blank in the Users & Roles UI.
    roles = {
        "admin": "System administrator (is_superuser grants actual access; this label is cosmetic)",
        "agent": "Full ticket and customer access",
        "front_desk": "Full ticket and customer access -- same permissions as agent, distinct label for job-scope clarity",
        "inventory_access": "Stackable add-on granting Inventory (assets/parts) access, independent of ticket/customer role",
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
    # Coarse-grained, per feature area -- one permission covers every
    # action within that area, rather than separate create/edit/delete
    # permissions per resource. Matches the shop's actual staffing model
    # (a handful of people, divided by job area, not by fine-grained
    # action) better than finer granularity would.
    permissions = [
        ("tickets.manage", "Create, edit, and view tickets"),
        ("customers.manage", "Create, edit, and view customers"),
        ("inventory.manage", "Create and edit assets and parts"),
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

    # Clean up permissions from an earlier, finer-grained scheme this
    # project briefly had (e.g. "ticket.create", "attachment.add") --
    # some of those named actions don't even correspond to a real
    # desktop feature yet (there's no Attachments UI at all), and none
    # of them are checked by any route anymore. RolePermission has no
    # cascade delete, so its rows pointing at a stale permission have
    # to go first or the permission delete would violate the foreign key.
    canonical_names = {name for name, _ in permissions}
    stale_permissions = db.query(Permission).filter(~Permission.name.in_(canonical_names)).all()
    for stale in stale_permissions:
        db.query(RolePermission).filter_by(permission_id=stale.id).delete()
        db.delete(stale)
    if stale_permissions:
        db.commit()

    # -------------------------------------------------------------------
    # Role -> Permission mapping
    # -------------------------------------------------------------------
    role_permission_grants = {
        "admin": ["tickets.manage", "customers.manage", "inventory.manage"],
        "agent": ["tickets.manage", "customers.manage"],
        "front_desk": ["tickets.manage", "customers.manage"],
        "inventory_access": ["inventory.manage"],
    }

    def assign_perms(role_name, perm_names):
        """Grant every permission in perm_names to the given role, skipping duplicates."""
        role = role_objs[role_name]
        for perm_name in perm_names:
            perm = perm_objs[perm_name]

            exists = (
                db.query(RolePermission)
                .filter_by(role_id=role.id, permission_id=perm.id)
                .first()
            )
            if not exists:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    for role_name, perm_names in role_permission_grants.items():
        assign_perms(role_name, perm_names)

    db.commit()

    # -------------------------------------------------------------------
    # Default admin user
    # -------------------------------------------------------------------
    admin_email = "admin@example.com"
    admin_user = db.query(User).filter_by(email=admin_email).first()

    if not admin_user:
        admin_user = User(
            email=admin_email,
            hashed_password=hash_password("Admin123!"),
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
            hashed_password=hash_password("Agent123!"),
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
    # Default front desk user
    # -------------------------------------------------------------------
    # Exists purely for testing that Agent and Front Desk actually see
    # identical access -- both roles currently grant the same
    # permissions, distinct only as job-scope labels (see the Roles
    # section above).
    front_desk_email = "frontdesk@example.com"
    front_desk_user = db.query(User).filter_by(email=front_desk_email).first()

    if not front_desk_user:
        front_desk_user = User(
            email=front_desk_email,
            hashed_password=hash_password("FrontDesk123!"),
            first_name="Front",
            last_name="Desk",
            is_active=True,
            is_superuser=False,
        )
        db.add(front_desk_user)
        db.commit()
        db.refresh(front_desk_user)

        db.add(UserRole(user_id=front_desk_user.id, role_id=role_objs["front_desk"].id))

    db.commit()

    # -------------------------------------------------------------------
    # Ticket statuses (high-level workflow state)
    # -------------------------------------------------------------------
    statuses = [
        ("Open", "Newly created, not yet started"),
        ("In Progress", "Actively being worked on"),
        ("Waiting on Parts", "Blocked pending a parts order"),
        ("Waiting on Customer", "Blocked pending customer response"),
        ("Resolved", "Work complete, pending pickup/close"),
        ("Closed", "Ticket fully closed"),
    ]
    status_objs = {}
    for name, desc in statuses:
        existing = db.query(TicketStatus).filter_by(name=name).first()
        if existing:
            status_objs[name] = existing
        else:
            obj = TicketStatus(name=name, description=desc)
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
    # Asset categories (organizes the shop's own tracked business assets,
    # distinct from ticket_categories which classify customer repair jobs)
    # -------------------------------------------------------------------
    asset_categories = [
        ("Laptop", "Shop-owned laptops"),
        ("Desktop", "Shop-owned desktop computers"),
        ("Monitor", "Displays and monitors"),
        ("Networking Equipment", "Routers, switches, access points"),
        ("Furniture", "Desks, chairs, shelving"),
        ("Tool", "Hand tools, diagnostic equipment"),
        ("Other", "Anything that doesn't fit an existing category"),
    ]
    for name, desc in asset_categories:
        if not db.query(AssetCategory).filter_by(name=name).first():
            db.add(AssetCategory(name=name, description=desc))
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

    # -------------------------------------------------------------------
    # Business name (set once, at first setup, via the Setup Wizard)
    # -------------------------------------------------------------------
    if business_name:
        existing_setting = db.query(SystemSetting).filter_by(key="business_name").first()
        if not existing_setting:
            db.add(SystemSetting(key="business_name", value=business_name))
            db.commit()

    print("Seed data inserted successfully.")
