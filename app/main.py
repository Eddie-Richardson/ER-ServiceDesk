# ER-ServiceDesk/app/main.py
# FastAPI application entrypoint
"""
Application entrypoint. Creates the FastAPI app, mounts every route
module, and exposes a health check endpoint for deployment/monitoring.
"""

from fastapi import FastAPI

from app.routes import (
    attachments,
    audit_logs,
    auth,
    background_jobs,
    customers,
    devices,
    invoices,
    message_templates,
    messages,
    notes,
    payments,
    permissions,
    quotes,
    role_permissions,
    roles,
    status_histories,
    system_settings,
    ticket_categories,
    ticket_statuses,
    ticket_types,
    tickets,
    user_roles,
    users,
)

app = FastAPI(title="ER Service Desk API")


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
app.include_router(tickets.router)
app.include_router(ticket_categories.router)
app.include_router(ticket_statuses.router)
app.include_router(ticket_types.router)
app.include_router(status_histories.router)

# Ticket-linked records
app.include_router(notes.router)
app.include_router(messages.router)
app.include_router(message_templates.router)
app.include_router(attachments.router)
app.include_router(quotes.router)
app.include_router(invoices.router)
app.include_router(payments.router)

# System / ops
app.include_router(audit_logs.router)
app.include_router(background_jobs.router)
app.include_router(system_settings.router)


@app.get("/health")
def health_check():
    """
    Report whether the API process is up.

    Returns:
        A static {"status": "ok"} payload. Used by load balancers,
        uptime monitors, and CI/CD deployment checks.
    """
    return {"status": "ok"}
