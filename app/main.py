# ER-ServiceDesk/app/main.py
# FastAPI application entrypoint
"""
Application entrypoint. Creates the FastAPI app, mounts every route
module, and exposes a health check endpoint for deployment/monitoring.
"""

from fastapi import FastAPI

from app.core.error_handlers import register_error_handlers
from app.core.logging_config import setup_logging

from app.routes import (
    assets,
    asset_categories,
    audit_logs,
    auth,
    background_jobs,
    business_info,
    customers,
    devices,
    device_user_accounts,
    discounts,
    invoices,
    locations,
    message_templates,
    messages,
    parts,
    payment_plans,
    payments,
    permissions,
    quotes,
    record_locks,
    role_permissions,
    roles,
    services,
    status_histories,
    system_settings,
    tax_rates,
    ticket_categories,
    ticket_parts,
    ticket_stages,
    ticket_statuses,
    ticket_type_stages,
    ticket_types,
    tickets,
    user_roles,
    users,
)

app = FastAPI(title="ER Service Desk API")

register_error_handlers(app)
setup_logging()


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
# Every route module defines its own prefix/tags; mounted here in one place
# so the full API surface is visible at a glance.

# Core RBAC / auth
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(roles.router)
app.include_router(permissions.router)
app.include_router(role_permissions.router)
app.include_router(user_roles.router)

# Customers, devices, tickets
app.include_router(customers.router)
app.include_router(devices.router)
app.include_router(device_user_accounts.router)
app.include_router(tickets.router)
app.include_router(ticket_categories.router)
app.include_router(ticket_stages.router)
app.include_router(ticket_statuses.router)
app.include_router(ticket_types.router)
app.include_router(ticket_type_stages.router)
app.include_router(status_histories.router)

# Ticket-linked records
app.include_router(messages.router)
app.include_router(message_templates.router)
app.include_router(quotes.router)
app.include_router(record_locks.router)
app.include_router(invoices.router)
app.include_router(payments.router)
app.include_router(payment_plans.router)
app.include_router(services.router)
app.include_router(discounts.router)
app.include_router(tax_rates.router)

# System / ops
app.include_router(audit_logs.router)
app.include_router(background_jobs.router)
app.include_router(business_info.router)
app.include_router(system_settings.router)

# Inventory (merged from InventoryHub)
app.include_router(locations.router)
app.include_router(assets.router)
app.include_router(asset_categories.router)
app.include_router(parts.router)
app.include_router(ticket_parts.router)


@app.get("/health")
def health_check():
    """
    Report whether the API process is up.

    Returns:
        A static {"status": "ok"} payload. Used by load balancers,
        uptime monitors, and CI/CD deployment checks.
    """
    return {"status": "ok"}
