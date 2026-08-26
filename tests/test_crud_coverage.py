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

from tests.factories import (
    make_customer,
    make_device,
    make_location,
    make_role,
    make_permission,
    make_plain_user,
    make_full_ticket,
    make_invoice,
)


def _assert_crud_lifecycle(client, headers, url, create_payload, update_payload, update_check_field=None, read_headers=None):
    """
    Drive a full CRUD lifecycle against a resource's routes and assert
    each step behaves correctly.

    Args:
        client: The TestClient fixture.
        headers: Auth header dict for a user allowed to create/update/delete.
        url: The resource's base URL, e.g. "/roles" (no trailing slash).
        create_payload: JSON body for the POST request.
        update_payload: JSON body for the PUT request.
        update_check_field: If given, asserts response[field] == update_payload[field]
            after the update -- confirms the update actually took effect,
            not just that the request returned 200.
        read_headers: Auth header dict for the list/get steps, if
            different from headers -- e.g. a resource where GET only
            requires billing.manage but writes require superuser. Uses
            headers for reads too if not given.

    Returns:
        The created record's response JSON, in case a test needs to
        inspect anything beyond what this helper already checks.
    """
    read_headers = read_headers if read_headers is not None else headers

    # Create
    create_resp = client.post(f"{url}/", json=create_payload, headers=headers)
    assert create_resp.status_code == 200, create_resp.text
    created = create_resp.json()
    assert "id" in created
    record_id = created["id"]

    # List includes it
    list_resp = client.get(f"{url}/", headers=read_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == record_id for item in list_resp.json())

    # Get by id
    get_resp = client.get(f"{url}/{record_id}", headers=read_headers)
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
    """UserRole is a pure join record -- add/remove is the real pattern (see RoleSaveWorker/UserSaveWorker), never an in-place edit. Update is confirmed rejected rather than tested as working."""
    user = make_plain_user(db)
    role = make_role(db)

    create_resp = client.post("/user_roles/", json={"user_id": user.id, "role_id": role.id}, headers=superuser_headers)
    assert create_resp.status_code == 200, create_resp.text
    user_role_id = create_resp.json()["id"]

    list_resp = client.get("/user_roles/", headers=superuser_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == user_role_id for item in list_resp.json())

    role2 = make_role(db, name="Manager")
    update_resp = client.put(f"/user_roles/{user_role_id}", json={"role_id": role2.id}, headers=superuser_headers)
    assert update_resp.status_code == 405

    delete_resp = client.delete(f"/user_roles/{user_role_id}", headers=superuser_headers)
    assert delete_resp.status_code in (200, 204)


def test_system_settings_crud(client, superuser_headers):
    _assert_crud_lifecycle(
        client, superuser_headers, "/system_settings",
        {"key": "support_email", "value": "help@example.com"},
        {"value": "support@example.com"},
        update_check_field="value",
    )


def test_audit_logs_is_read_only(client, superuser_headers):
    """AuditLog is a deliberately immutable, internally-generated record -- no create/update/delete route exists at all, only listing."""
    list_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert list_resp.status_code == 200
    create_resp = client.post("/audit_logs/", json={"action": "login", "entity_type": "user", "entity_id": 1}, headers=superuser_headers)
    assert create_resp.status_code == 405


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
        {"name": "In Progress", "description": "Actively being worked"},
        {"description": "Currently on the bench"},
        update_check_field="description",
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


def test_background_jobs_is_read_only(client, agent_headers):
    """BackgroundJob is a deliberately immutable, internally-generated record (created only by worker tasks, via start()/complete()/fail()) -- no create route exists via the API, only listing."""
    list_resp = client.get("/background_jobs/", headers=agent_headers)
    assert list_resp.status_code == 200
    create_resp = client.post("/background_jobs/", json={"job_type": "send_email", "status": "queued"}, headers=agent_headers)
    assert create_resp.status_code == 405


def test_message_templates_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/message_templates",
        {"name": "ticket_created", "body": "We got your ticket."},
        {"body": "We received your repair request."},
        update_check_field="body",
    )


def test_locations_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/inventory/locations",
        {"name": "Front Counter", "description": "Customer-facing intake area", "show_in_ticket_picker": True},
        {"description": "Main intake and pickup area", "show_in_ticket_picker": False},
        update_check_field="show_in_ticket_picker",
    )


def test_customers_crud(client, agent_headers):
    _assert_crud_lifecycle(
        client, agent_headers, "/customers",
        {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "street": "123 Main St", "city": "Dallas", "state": "TX", "zip_code": "75001"},
        {"phone": "555-1234", "street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "zip_code": "90210"},
        update_check_field="city",
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


def test_device_create_and_update_appear_in_audit_log(client, superuser_headers, db):
    """Regression test: device_service.create()/update() previously never logged to the audit trail at all -- only delete() did, so no device creation or edit ever showed up in the Audit Log."""
    customer = make_customer(db)

    create_resp = client.post("/devices/", json={"customer_id": customer.id, "device_type": "Laptop", "brand": "Dell", "model": "Latitude 5420"}, headers=superuser_headers)
    assert create_resp.status_code == 200, create_resp.text
    device_id = create_resp.json()["id"]

    update_resp = client.put(f"/devices/{device_id}", json={"brand": "HP"}, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert audit_resp.status_code == 200
    actions = [entry["action"] for entry in audit_resp.json() if entry["entity_type"] == "device" and entry["entity_id"] == device_id]
    assert "device_created" in actions
    assert "device_updated" in actions


# ---------------------------------------------------------------------------
# Resources needing a full Ticket
# ---------------------------------------------------------------------------

def test_messages_crud(client, superuser_headers, db):
    """Covers the internal-note case specifically -- not outbound/inbound sending or the author-or-superuser authorization rule."""
    ticket = make_full_ticket(db)
    user = make_plain_user(db)
    _assert_crud_lifecycle(
        client, superuser_headers, "/messages",
        {"ticket_id": ticket.id, "user_id": user.id, "direction": "internal", "content": "Internal note"},
        {"content": "Updated internal note"},
        update_check_field="content",
    )


def test_quotes_crud(client, agent_headers, db):
    """Quote creation starts empty (ticket_id only) -- line items get added separately, one at a time, via their own endpoint. Quotes are otherwise not deletable (financial record), except for the one narrow case exercised here: an empty, never-sent, never-converted quote that's also still the most recently created one."""
    ticket = make_full_ticket(db)

    create_resp = client.post("/quotes/", json={"ticket_id": ticket.id, "details": "Screen + labor"}, headers=agent_headers)
    assert create_resp.status_code == 200, create_resp.text
    quote_id = create_resp.json()["id"]

    list_resp = client.get("/quotes/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == quote_id for item in list_resp.json())

    get_resp = client.get(f"/quotes/{quote_id}", headers=agent_headers)
    assert get_resp.status_code == 200

    update_resp = client.put(f"/quotes/{quote_id}", json={"details": "Screen replacement + labor"}, headers=agent_headers)
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["details"] == "Screen replacement + labor"

    delete_resp = client.delete(f"/quotes/{quote_id}", headers=agent_headers)
    assert delete_resp.status_code == 200, delete_resp.text

    get_after_delete_resp = client.get(f"/quotes/{quote_id}", headers=agent_headers)
    assert get_after_delete_resp.status_code == 404


def test_convert_quote_to_invoice(client, agent_headers, superuser_headers, db):
    """
    Converting a quote copies every line item over to the new invoice --
    both service-based and part-based ones -- along with the discount/tax
    selection and totals, then links the quote to the invoice it became.
    Regression test: a real positional-argument mismatch in the copy loop
    (service_id/service_name landing in the quantity/unit_price slots,
    and part-based line items never being copied at all) shipped
    undetected since nothing exercised this path before. Also covers a
    second, separate gap found afterward: convert_to_invoice() copied
    line item data but never triggered inventory deduction for
    part-based ones, since it bypasses add_line_item() entirely --
    only the direct-invoice-line-item path deducted stock before this.
    """
    ticket = make_full_ticket(db)
    location = make_location(db)
    location_setting_resp = client.put("/system_settings/by-key/part_deduction_location_id", json={"value": str(location.id)}, headers=superuser_headers)
    assert location_setting_resp.status_code == 200, location_setting_resp.text

    service_resp = client.post("/services/", json={"name": "Diagnostic", "price": 50.0}, headers=superuser_headers)
    assert service_resp.status_code == 200, service_resp.text
    service_id = service_resp.json()["id"]

    part_resp = client.post("/inventory/parts/", json={"name": "SSD 500GB", "sku": "SKU-CONVERT-001", "selling_price": 80.0}, headers=superuser_headers)
    assert part_resp.status_code == 200, part_resp.text
    part_id = part_resp.json()["id"]

    quote_resp = client.post("/quotes/", json={"ticket_id": ticket.id}, headers=agent_headers)
    assert quote_resp.status_code == 200, quote_resp.text
    quote_id = quote_resp.json()["id"]

    add_service_resp = client.post(f"/quotes/{quote_id}/line-items", params={"service_id": service_id, "quantity": 1}, headers=agent_headers)
    assert add_service_resp.status_code == 200, add_service_resp.text

    add_part_resp = client.post(f"/quotes/{quote_id}/line-items", params={"part_id": part_id, "quantity": 2}, headers=agent_headers)
    assert add_part_resp.status_code == 200, add_part_resp.text

    convert_resp = client.post(f"/quotes/{quote_id}/convert-to-invoice", headers=agent_headers)
    assert convert_resp.status_code == 200, convert_resp.text
    invoice = convert_resp.json()
    invoice_id = invoice["id"]

    invoice_line_items = invoice["line_items"]
    assert len(invoice_line_items) == 2

    service_line = next(li for li in invoice_line_items if li["service_id"] == service_id)
    assert service_line["service_name"] == "Diagnostic"
    assert service_line["quantity"] == 1
    assert float(service_line["unit_price"]) == 50.0
    assert service_line["part_id"] is None

    part_line = next(li for li in invoice_line_items if li["part_id"] == part_id)
    assert part_line["part_name"] == "SSD 500GB"
    assert part_line["quantity"] == 2
    assert float(part_line["unit_price"]) == 80.0
    assert part_line["service_id"] is None

    quote_after_resp = client.get(f"/quotes/{quote_id}", headers=agent_headers)
    quote_after = quote_after_resp.json()
    assert quote_after["converted_invoice_id"] == invoice_id
    assert quote_after["converted_invoice_number"] == invoice["invoice_number"]

    part_after_resp = client.get(f"/inventory/parts/{part_id}", headers=agent_headers)
    assert part_after_resp.status_code == 200
    part_location = next(loc for loc in part_after_resp.json()["locations"] if loc["location_id"] == location.id)
    assert part_location["quantity"] == -2  # started at 0 (no initial stock breakdown), 2 units deducted


def test_tax_rates_crud(client, agent_headers, superuser_headers):
    """GET requires billing.manage (agent_headers has it); create/update/delete require superuser specifically."""
    _assert_crud_lifecycle(
        client, superuser_headers, "/tax_rates",
        {"name": "Sales Tax", "percentage": "7.25"},
        {"percentage": "8.00"},
        update_check_field="percentage",
        read_headers=agent_headers,
    )


def test_tax_rates_write_requires_superuser(client, agent_headers):
    """billing.manage alone isn't enough to create a tax rate -- catalog writes are superuser-only, matching services.py's own gating split."""
    resp = client.post("/tax_rates/", json={"name": "VAT", "percentage": "20.00"}, headers=agent_headers)
    assert resp.status_code == 403


def test_discounts_crud(client, agent_headers, superuser_headers):
    """GET requires billing.manage (agent_headers has it); create/update/delete require superuser specifically."""
    _assert_crud_lifecycle(
        client, superuser_headers, "/discounts",
        {"name": "Loyalty Discount", "percentage": "10.00"},
        {"percentage": "15.00"},
        update_check_field="percentage",
        read_headers=agent_headers,
    )


def test_discounts_write_requires_superuser(client, agent_headers):
    """billing.manage alone isn't enough to create a discount -- catalog writes are superuser-only."""
    resp = client.post("/discounts/", json={"name": "Referral", "percentage": "5.00"}, headers=agent_headers)
    assert resp.status_code == 403


def test_services_crud(client, agent_headers, superuser_headers):
    """GET requires billing.manage (agent_headers has it); create/update/delete require superuser specifically."""
    _assert_crud_lifecycle(
        client, superuser_headers, "/services",
        {"name": "Diagnostic", "price": "50.00"},
        {"price": "60.00"},
        update_check_field="price",
        read_headers=agent_headers,
    )


def test_services_write_requires_superuser(client, agent_headers):
    """billing.manage alone isn't enough to create a service -- catalog writes are superuser-only."""
    resp = client.post("/services/", json={"name": "Cleaning", "price": "25.00"}, headers=agent_headers)
    assert resp.status_code == 403


def test_asset_categories_crud(client, agent_headers):
    """Only requires a logged-in user -- no special permission gating, unlike the billing catalogs above."""
    _assert_crud_lifecycle(
        client, agent_headers, "/inventory/asset_categories",
        {"name": "Laptop", "description": "Portable computers"},
        {"description": "Portable computers and tablets"},
        update_check_field="description",
    )


def test_business_info_settings_requires_superuser(client, agent_headers):
    """billing.manage/other ordinary permissions aren't enough -- this screen includes setting the email password, so it's superuser-only, no exceptions."""
    resp = client.get("/business_info_settings/", headers=agent_headers)
    assert resp.status_code == 403


def test_business_info_settings_password_never_returned(client, superuser_headers):
    """Setting an email password never gets it back out through the API -- only whether one is set."""
    payload = {
        "business_name": "Eddie's Repair Shop", "business_phone": "555-0100",
        "email_address": "shop@example.com", "email_password": "a-genuinely-secret-value",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "imap_host": "imap.gmail.com", "imap_port": 993,
    }
    update_resp = client.put("/business_info_settings/", json=payload, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["email_password_is_set"] is True
    assert "a-genuinely-secret-value" not in update_resp.text

    get_resp = client.get("/business_info_settings/", headers=superuser_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["email_password_is_set"] is True
    assert "a-genuinely-secret-value" not in get_resp.text


def test_business_info_settings_omitted_password_leaves_existing_one(client, superuser_headers):
    """Updating other fields without sending email_password keeps the previously-set password, rather than wiping it out."""
    initial_payload = {
        "business_name": "Eddie's Repair Shop", "business_phone": "555-0100",
        "email_address": "shop@example.com", "email_password": "the-original-password",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "imap_host": "imap.gmail.com", "imap_port": 993,
    }
    first_resp = client.put("/business_info_settings/", json=initial_payload, headers=superuser_headers)
    assert first_resp.status_code == 200, first_resp.text
    assert first_resp.json()["email_password_is_set"] is True

    followup_payload = dict(initial_payload)
    followup_payload["business_phone"] = "555-0199"
    followup_payload["email_password"] = None
    second_resp = client.put("/business_info_settings/", json=followup_payload, headers=superuser_headers)
    assert second_resp.status_code == 200, second_resp.text
    assert second_resp.json()["business_phone"] == "555-0199"
    assert second_resp.json()["email_password_is_set"] is True


def test_business_info_narrow_endpoint_reflects_the_same_name(client, agent_headers, superuser_headers):
    """business-info's narrow, any-logged-in-user endpoint reads the same business_name set through the full superuser management screen -- confirming the two genuinely share one underlying setting, not two separate values."""
    payload = {
        "business_name": "Shared Name Shop", "business_phone": "555-0100",
        "email_address": "shop@example.com",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "imap_host": "imap.gmail.com", "imap_port": 993,
    }
    update_resp = client.put("/business_info_settings/", json=payload, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    narrow_resp = client.get("/business-info/business-name", headers=agent_headers)
    assert narrow_resp.status_code == 200
    assert narrow_resp.json()["business_name"] == "Shared Name Shop"


def test_device_user_account_password_round_trips_correctly(client, agent_headers, db):
    """A password set through create() comes back as the exact same plaintext -- confirms the encrypt/decrypt round-trip genuinely works, not just that the API returns some value."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    create_resp = client.post(
        "/device_user_accounts/",
        json={"device_id": device.id, "account_name": "jsmith@outlook.com", "password": "Correct-Horse-Battery-Staple-9", "is_admin": False},
        headers=agent_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    account_id = create_resp.json()["id"]
    assert create_resp.json()["password"] == "Correct-Horse-Battery-Staple-9"

    list_resp = client.get("/device_user_accounts/", params={"device_id": device.id}, headers=agent_headers)
    assert list_resp.status_code == 200
    listed = next(a for a in list_resp.json() if a["id"] == account_id)
    assert listed["password"] == "Correct-Horse-Battery-Staple-9"


def test_device_user_account_password_update_and_omit_behavior(client, agent_headers, db):
    """Updating with a new password replaces it; updating other fields while omitting password leaves the existing one unchanged."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    create_resp = client.post(
        "/device_user_accounts/",
        json={"device_id": device.id, "account_name": "jsmith@outlook.com", "password": "original-password", "is_admin": False},
        headers=agent_headers,
    )
    account_id = create_resp.json()["id"]

    new_password_resp = client.put(f"/device_user_accounts/{account_id}", json={"password": "replaced-password"}, headers=agent_headers)
    assert new_password_resp.status_code == 200, new_password_resp.text
    assert new_password_resp.json()["password"] == "replaced-password"

    rename_only_resp = client.put(f"/device_user_accounts/{account_id}", json={"account_name": "jsmith-renamed@outlook.com"}, headers=agent_headers)
    assert rename_only_resp.status_code == 200, rename_only_resp.text
    assert rename_only_resp.json()["account_name"] == "jsmith-renamed@outlook.com"
    assert rename_only_resp.json()["password"] == "replaced-password"


def test_device_user_account_delete(client, agent_headers, db):
    customer = make_customer(db)
    device = make_device(db, customer.id)

    create_resp = client.post(
        "/device_user_accounts/",
        json={"device_id": device.id, "account_name": "temp@outlook.com", "password": "temp-pass", "is_admin": True},
        headers=agent_headers,
    )
    account_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/device_user_accounts/{account_id}", headers=agent_headers)
    assert delete_resp.status_code in (200, 204)

    list_resp = client.get("/device_user_accounts/", params={"device_id": device.id}, headers=agent_headers)
    assert not any(a["id"] == account_id for a in list_resp.json())


def test_device_user_accounts_list_requires_device_id(client, agent_headers):
    """device_id is a required query param, not optional -- there's no legitimate reason to fetch every device's accounts across the whole app at once."""
    resp = client.get("/device_user_accounts/", headers=agent_headers)
    assert resp.status_code == 422


def _make_invoice_with_total(db, total):
    """Sets a real, known total directly via the DB session, bypassing line-item calculation -- that's a separate concern from the payment-plan math these tests exercise."""
    from decimal import Decimal
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = Decimal(str(total))
    db.commit()
    db.refresh(invoice)
    return invoice


def test_payment_plan_create_splits_balance_correctly(client, agent_headers, db):
    """A $250 balance at $100/installment produces two full $100 installments plus a $50 remainder installment -- the last one gets whatever's left, never more than the entered amount."""
    invoice = _make_invoice_with_total(db, "250.00")

    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-31"},
        headers=agent_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    plan = create_resp.json()
    installments = plan["installments"]
    assert len(installments) == 3
    assert [i["planned_amount"] for i in installments] == ["100.00", "100.00", "50.00"]


def test_payment_plan_rejects_second_plan_on_same_invoice(client, agent_headers, db):
    invoice = _make_invoice_with_total(db, "100.00")
    first_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "50.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    assert first_resp.status_code == 200, first_resp.text

    second_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "25.00", "frequency": "weekly", "start_date": "2026-02-01"},
        headers=agent_headers,
    )
    assert second_resp.status_code == 400


def test_payment_plan_rejects_nonpositive_installment_amount(client, agent_headers, db):
    invoice = _make_invoice_with_total(db, "100.00")
    resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "0.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    assert resp.status_code == 400


def test_payment_plan_paying_exactly_as_scheduled_leaves_remaining_amounts_unchanged(client, agent_headers, db):
    """Paying the first installment for exactly its planned amount shouldn't change the remaining installments' amounts -- a sanity check that the rebalancing math is a no-op when there's no actual deviation."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 2
    assert [i["planned_amount"] for i in remaining] == ["100.00", "100.00"]


def test_payment_plan_overpaying_reduces_remaining_installments(client, agent_headers, db):
    """Overpaying one installment reduces what's redistributed across the rest, rather than leaving them at their original planned amount."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "150.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 2
    # $300 total - $150 paid = $150 remaining, split evenly across 2 installments
    assert [i["planned_amount"] for i in remaining] == ["75.00", "75.00"]


def test_payment_plan_underpaying_increases_remaining_installments(client, agent_headers, db):
    """Underpaying one installment (not the last) increases what's redistributed across the rest."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "50.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 2
    # $300 total - $50 paid = $250 remaining, split evenly across 2 installments
    assert [i["planned_amount"] for i in remaining] == ["125.00", "125.00"]


def test_payment_plan_overpaying_by_a_full_installment_marks_the_next_one_paid(client, agent_headers, db):
    """
    Eddie's own example: a $20/week plan, paying $40 against the first
    installment should mark the next installment paid too (fully
    covered by the extra $20), not just reduce what's owed on it.
    """
    invoice = _make_invoice_with_total(db, "80.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "20.00", "frequency": "weekly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    assert len(installments) == 4
    first_id = installments[0]["id"]
    second_id = installments[1]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "40.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    plan_installments = plan_resp.json()["installments"]

    first = next(i for i in plan_installments if i["id"] == first_id)
    second = next(i for i in plan_installments if i["id"] == second_id)
    assert first["payment_id"] is not None
    assert second["payment_id"] is not None
    assert second["payment_id"] == first["payment_id"]  # one real $40 transaction, not two fabricated $20 ones

    remaining = [i for i in plan_installments if i["payment_id"] is None]
    assert len(remaining) == 2
    assert [i["planned_amount"] for i in remaining] == ["20.00", "20.00"]  # untouched -- no leftover to redistribute


def test_payment_plan_overpaying_partway_into_the_next_installment_covers_it_then_redistributes(client, agent_headers, db):
    """
    A partial overpayment into the next installment -- enough to fully
    cover it, with some left over that's not enough for the one after
    that -- marks the covered one paid, then redistributes only the
    genuine leftover across what's still actually remaining.
    """
    invoice = _make_invoice_with_total(db, "80.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "20.00", "frequency": "weekly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]
    second_id = installments[1]["id"]

    # $50 paid: $20 covers the first installment, $20 more fully
    # covers the second, $10 left over redistributes across the
    # remaining 2 installments.
    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "50.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    plan_installments = plan_resp.json()["installments"]

    second = next(i for i in plan_installments if i["id"] == second_id)
    assert second["payment_id"] is not None

    remaining = [i for i in plan_installments if i["payment_id"] is None]
    assert len(remaining) == 2
    # $80 total - $50 paid = $30 remaining, split evenly across 2 installments
    assert [i["planned_amount"] for i in remaining] == ["15.00", "15.00"]


def test_payment_plan_overpaying_to_zero_completes_early(client, agent_headers, db):
    """Paying enough to reach a zero remaining balance deletes the leftover installments and marks the plan completed, rather than leaving zero-dollar installments behind."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "300.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    plan = plan_resp.json()
    assert plan["status"] == "completed"
    remaining = [i for i in plan["installments"] if i["payment_id"] is None]
    assert len(remaining) == 0


def test_payment_plan_underpaying_last_installment_appends_a_new_one(client, agent_headers, db):
    """Underpaying the final installment appends a new installment for what's left, since there's no other installment to redistribute onto."""
    invoice = _make_invoice_with_total(db, "100.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    assert len(installments) == 1
    only_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{only_id}/pay", json={"amount": "60.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 1
    assert remaining[0]["planned_amount"] == "40.00"
    assert remaining[0]["sequence_number"] == 2


def test_payment_plan_extend_date_uses_direct_offset_not_incremental(client, agent_headers, db):
    """
    Regression test for the documented Jan 31 date-extension bug class:
    extending an installment to Jan 31 and recalculating a later monthly
    installment must land on Mar 31, not Mar 28 -- incremental month-by-
    month math (Jan 31 -> Feb 28 -> Mar 28) silently loses the original
    day-of-month once a shorter month clamps it down.
    """
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]
    third_id = installments[2]["id"]

    extend_resp = client.put(f"/payment_plans/installments/{first_id}/extend", json={"new_due_date": "2026-01-31"}, headers=agent_headers)
    assert extend_resp.status_code == 200, extend_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    third_installment = next(i for i in plan_resp.json()["installments"] if i["id"] == third_id)
    assert third_installment["due_date"] == "2026-03-31"


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


def test_status_histories_is_read_only(client, agent_headers, db):
    """StatusHistory is a deliberately immutable, internally-generated record (created only when a ticket's status actually changes) -- no create route exists via the API, only listing."""
    from tests.factories import make_ticket_status
    ticket = make_full_ticket(db)
    status2 = make_ticket_status(db, name="Closed")
    user = make_plain_user(db)

    list_resp = client.get("/status_histories/", headers=agent_headers)
    assert list_resp.status_code == 200

    create_resp = client.post("/status_histories/", json={"ticket_id": ticket.id, "status_id": status2.id, "changed_by": user.id}, headers=agent_headers)
    assert create_resp.status_code == 405


# ---------------------------------------------------------------------------
# Resources needing an Invoice (which needs a Ticket)
# ---------------------------------------------------------------------------

def test_invoices_crud(client, agent_headers, db):
    """Invoice creation starts empty (ticket_id only), same as Quote. Invoices are otherwise not deletable (financial record); this one is additionally blocked because it's marked paid -- see test_quotes_crud for the narrow empty/unsent/most-recent case where deletion succeeds."""
    ticket = make_full_ticket(db)

    create_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    assert create_resp.status_code == 200, create_resp.text
    invoice_id = create_resp.json()["id"]

    list_resp = client.get("/invoices/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == invoice_id for item in list_resp.json())

    get_resp = client.get(f"/invoices/{invoice_id}", headers=agent_headers)
    assert get_resp.status_code == 200

    update_resp = client.put(f"/invoices/{invoice_id}", json={"is_paid": True}, headers=agent_headers)
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["is_paid"] is True

    delete_resp = client.delete(f"/invoices/{invoice_id}", headers=agent_headers)
    assert delete_resp.status_code == 400


def test_payments_crud(client, agent_headers, db):
    """Editing a recorded payment in place is deliberately not supported -- it would leave no trail and wouldn't trigger a corrected receipt. Delete-and-re-record is the correct pattern instead; update is confirmed rejected."""
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)

    create_resp = client.post("/payments/", json={"invoice_id": invoice.id, "amount": 200.0, "method": "cash"}, headers=agent_headers)
    assert create_resp.status_code == 200, create_resp.text
    payment_id = create_resp.json()["id"]

    list_resp = client.get("/payments/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == payment_id for item in list_resp.json())

    update_resp = client.put(f"/payments/{payment_id}", json={"method": "credit_card"}, headers=agent_headers)
    assert update_resp.status_code == 405

    delete_resp = client.delete(f"/payments/{payment_id}", headers=agent_headers)
    assert delete_resp.status_code in (200, 204)


# ---------------------------------------------------------------------------
# Inventory resources (assets/parts already have duplicate-check coverage
# in test_inventory.py -- this adds the missing full-lifecycle coverage)
# ---------------------------------------------------------------------------

def test_assets_crud(client, agent_headers):
    """
    Assets intentionally deviate from the generic CRUD response shape
    (wrapped create response, paginated list response). Tested directly
    rather than via the generic helper, which assumes the plain shape
    every other resource uses.
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


def test_parts_crud(client, agent_headers, db):
    from tests.factories import make_location
    location = make_location(db)
    _assert_crud_lifecycle(
        client, agent_headers, "/inventory/parts",
        {"name": "SATA Cable", "sku": "SATA-001", "reorder_threshold": 2, "locations": [{"location_id": location.id, "quantity": 10}]},
        {"reorder_threshold": 3},
        update_check_field="reorder_threshold",
    )
