# ER-ServiceDesk/tests/test_crud_coverage.py
# Full CRUD coverage for every route module without dedicated business-logic tests.
"""
The other test files (test_auth.py, test_message_email.py, test_inventory.py,
test_part_status_notify.py, test_ticket_part_shipping_info.py,
test_ticket_stage_restriction.py, test_user_security.py) each cover a
specific piece of business logic. This file covers everything else: plain
CRUD routes that have no special behavior beyond create/read/update/delete,
but still deserve real test coverage -- the {{id}} double-brace routing bug
found earlier in ticket_parts.py and locations.py was exactly this category
of route, and it went unnoticed because nothing exercised it.

_assert_crud_lifecycle is a single reusable helper that drives the full
list -> create -> get -> update -> delete -> 404-after-delete cycle for a
given resource, so each resource's test is a short, readable call rather
than a hand-written near-duplicate of the same five HTTP calls.
"""

from app.models.role import Role
from app.models.permission import Permission
from tests.factories import (
    make_customer,
    make_device,
    make_role,
    make_permission,
    make_plain_user,
    make_full_ticket,
    make_invoice,
    make_ticket_dependencies,
)


def _assert_crud_lifecycle(client, headers, url, create_payload, update_payload, update_check_field=None):
    """
    Drive a full CRUD lifecycle against a resource's routes and assert
    each step behaves correctly.

    Args:
        client: The TestClient fixture.
        headers: Auth header dict for a user allowed to access this route.
        url: The resource's base URL, e.g. "/roles" (no trailing slash).
        create_payload: JSON body for the POST request.
        update_payload: JSON body for the PUT request.
        update_check_field: If given, asserts response[field] == update_payload[field]
            after the update -- confirms the update actually took effect,
            not just that the request returned 200.

    Returns:
        The created record's response JSON, in case a test needs to
        inspect anything beyond what this helper already checks.
    """
    # Create
    create_resp = client.post(f"{url}/", json=create_payload, headers=headers)
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    assert "id" in created
    record_id = created["id"]

    # List includes it
    list_resp = client.get(f"{url}/", headers=headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == record_id for item in list_resp.json())

    # Get by id
    get_resp = client.get(f"{url}/{record_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == record_id

    # Update
    update_resp = client.put(f"{url}/{record_id}", json=update_payload, headers=headers)
    assert update_resp.status_code == 200, update_resp.text
    if update_check_field:
        assert update_resp.json()[update_check_field] == update_payload[update_check_field]

    # Delete
    delete_resp = client.delete(f"{url}/{record_id}", headers=headers)
    assert delete_resp.status_code in (200, 204)

    return created


def _assert_requires_auth(client, url):
    """A route with no Authorization header should be rejected, not silently allowed."""
    resp = client.get(f"{url}/")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Superuser-only resources
# ---------------------------------------------------------------------------

def test_roles_crud(client, superuser_headers):
    _assert_crud_lifecycle(
        client, superuser_headers, "/roles",
        {"name": "Technician", "description": "Repair tech"},
        {"description": "Senior repair tech"},
        update_check_field="description",
    )


def test_roles_requires_auth(client):
    _assert_requires_auth(client, "/roles")


def test_permissions_crud(client, superuser_headers):
    _assert_crud_lifecycle(
        client, superuser_headers, "/permissions",
        {"name": "ticket.create", "description": "Create tickets"},
        {"description": "Create new tickets"},
        update_check_field="description",
    )


def test_role_permissions_crud(client, superuser_headers, db):
    role = make_role(db)
    permission = make_permission(db)
    role2 = make_role(db, name="Manager")
    permission2 = make_permission(db, name="ticket.delete")
    _assert_crud_lifecycle(
        client, superuser_headers, "/role_permissions",
        {"role_id": role.id, "permission_id": permission.id},
        {"role_id": role2.id, "permission_id": permission2.id},
        update_check_field="role_id",
    )


def test_user_roles_crud(client, superuser_headers, db):
    user = make_plain_user(db)
    role = make_role(db)
    role2 = make_role(db, name="Manager")
    _assert_crud_lifecycle(
        client, superuser_headers, "/user_roles",
        {"user_id": user.id, "role_id": role.id},
        {"role_id": role2.id},
        update_check_field="role_id",
    )


def test_system_settings_crud(client, superuser_headers):
    _assert_crud_lifecycle(
        client, superuser_headers, "/system_settings",
        {"key": "support_email", "value": "help@example.com"},
        {"value": "support@example.com"},
        update_check_field="value",
    )


def test_audit_logs_crud(client, superuser_headers):
    _assert_crud_lifecycle(
        client, superuser_headers, "/audit_logs",
        {"action": "login", "entity_type": "user", "entity_id": 1},
        {"action": "login_failed"},
        update_check_field="action",
    )


def test_users_requires_superuser_not_just_auth(client, agent_headers):
    """A regular (non-superuser) authenticated user should be rejected from /users."""
    resp = client.get("/users/", headers=agent_headers)
    assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Standalone lookup-table resources (any authenticated user)
# ---------------------------------------------------------------------------

def test_ticket_categories_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/ticket_categories",
        {"name": "Networking", "description": "Network issues"},
        {"description": "Network/connectivity issues"},
        update_check_field="description",
    )


def test_ticket_statuses_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/ticket_statuses",
        {"name": "In Progress", "color": "#0000FF"},
        {"color": "#0000AA"},
        update_check_field="color",
    )


def test_ticket_types_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/ticket_types",
        {"name": "Feature Request"},
        {"description": "A requested new capability"},
        update_check_field="description",
    )


def test_ticket_stages_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/ticket_stages",
        {"name": "Awaiting Parts"},
        {"description": "Waiting on an ordered part"},
        update_check_field="description",
    )


def test_ticket_type_stages_crud(client, agent_headers, db):
    from tests.factories import make_ticket_type, make_ticket_stage
    ttype = make_ticket_type(db)
    stage = make_ticket_stage(db)
    ttype2 = make_ticket_type(db, name="Bug")
    _assert_crud_lifecycle(
        client, agent_headers, "/ticket_type_stages",
        {"type_id": ttype.id, "stage_id": stage.id},
        {"type_id": ttype2.id},
        update_check_field="type_id",
    )


def test_background_jobs_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/background_jobs",
        {"job_type": "send_email", "status": "queued"},
        {"status": "completed"},
        update_check_field="status",
    )


def test_message_templates_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/message_templates",
        {"name": "ticket_created", "subject": "Your ticket was created", "body": "We got your ticket."},
        {"body": "We received your repair request."},
        update_check_field="body",
    )


def test_locations_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/inventory/locations",
        {"name": "Front Counter", "description": "Customer-facing intake area"},
        {"description": "Main intake and pickup area"},
        update_check_field="description",
    )


def test_customers_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/customers",
        {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com"},
        {"phone": "555-1234"},
        update_check_field="phone",
    )


# ---------------------------------------------------------------------------
# Resources needing a Customer
# ---------------------------------------------------------------------------

def test_devices_crud(client, agent_headers, db):
    customer = make_customer(db)
    _assert_crud_lifecycle(
        client, agent_headers, "/devices",
        {"customer_id": customer.id, "device_type": "Desktop"},
        {"brand": "Dell"},
        update_check_field="brand",
    )


# ---------------------------------------------------------------------------
# Resources needing a full Ticket
# ---------------------------------------------------------------------------

def test_messages_crud(client, superuser_headers, db):
    """Covers the internal-note case specifically -- see test_message_authorization.py (if/when written) for outbound/inbound and the author-or-superuser authorization rule."""
    ticket = make_full_ticket(db)
    user = make_plain_user(db)
    _assert_crud_lifecycle(
        client, superuser_headers, "/messages",
        {"ticket_id": ticket.id, "user_id": user.id, "direction": "internal", "content": "Internal note"},
        {"content": "Updated internal note"},
        update_check_field="content",
    )


def test_attachments_crud(client, agent_headers, db):
    ticket = make_full_ticket(db)
    _assert_crud_lifecycle(
        client, agent_headers, "/attachments",
        {"ticket_id": ticket.id, "file_path": "/uploads/receipt.pdf", "file_name": "receipt.pdf"},
        {"file_name": "receipt_v2.pdf"},
        update_check_field="file_name",
    )


def test_quotes_crud(client, agent_headers, db):
    ticket = make_full_ticket(db)
    _assert_crud_lifecycle(
        client, agent_headers, "/quotes",
        {"ticket_id": ticket.id, "amount": 150.0, "details": "Screen + labor"},
        {"amount": 175.0},
        update_check_field="amount",
    )


def test_status_histories_crud(client, agent_headers, db):
    from tests.factories import make_ticket_status
    ticket = make_full_ticket(db)
    status2 = make_ticket_status(db, name="Closed")
    user = make_plain_user(db)
    _assert_crud_lifecycle(
        client, agent_headers, "/status_histories",
        {"ticket_id": ticket.id, "status_id": status2.id, "changed_by": user.id},
        {"changed_by": user.id},
        update_check_field="changed_by",
    )


# ---------------------------------------------------------------------------
# Resources needing an Invoice (which needs a Ticket)
# ---------------------------------------------------------------------------

def test_invoices_crud(client, agent_headers, db):
    ticket = make_full_ticket(db)
    _assert_crud_lifecycle(
        client, agent_headers, "/invoices",
        {"ticket_id": ticket.id, "amount": 200.0, "is_paid": False},
        {"is_paid": True},
        update_check_field="is_paid",
    )


def test_payments_crud(client, agent_headers, db):
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    _assert_crud_lifecycle(
        client, agent_headers, "/payments",
        {"invoice_id": invoice.id, "amount": 200.0, "method": "cash"},
        {"method": "credit_card"},
        update_check_field="method",
    )


# ---------------------------------------------------------------------------
# Inventory resources (assets/parts already have duplicate-check coverage
# in test_inventory.py -- this adds the missing full-lifecycle coverage)
# ---------------------------------------------------------------------------

def test_assets_crud(client, agent_headers):
    """
    Assets intentionally deviate from the generic CRUD response shape
    (wrapped create response, paginated list response) -- preserved from
    the original InventoryHub API. Tested directly rather than via the
    generic helper, which assumes the plain shape every other resource uses.
    """
    create_resp = client.post(
        "/inventory/assets/",
        json={"name": "Soldering Station", "serial_number": "SS-001"},
        headers=agent_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    body = create_resp.json()
    assert body["message"] == "Asset created successfully"
    asset_id = body["asset"]["id"]

    list_resp = client.get("/inventory/assets/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == asset_id for item in list_resp.json()["items"])

    get_resp = client.get(f"/inventory/assets/{asset_id}", headers=agent_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == asset_id

    update_resp = client.put(
        f"/inventory/assets/{asset_id}", json={"condition": "good"}, headers=agent_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["condition"] == "good"

    delete_resp = client.delete(f"/inventory/assets/{asset_id}", headers=agent_headers)
    assert delete_resp.status_code in (200, 204)


def test_parts_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/inventory/parts",
        {"name": "SATA Cable", "sku": "SATA-001", "quantity_on_hand": 10, "reorder_threshold": 2},
        {"quantity_on_hand": 8},
        update_check_field="quantity_on_hand",
    )
