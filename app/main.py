# ER-ServiceDesk/app/main.py
# FastAPI application entrypoint
#
# This module serves as the main entrypoint for the ER‑ServiceDesk API.
# It initializes the FastAPI application, configures global settings such
# as the project title, and exposes core routes like the health check
# endpoint used for uptime monitoring and deployment validation.

from fastapi import FastAPI
from app.routes import users
from app.routes import tickets
from app.routes import comments
from app.routes import attachments
from app.routes import auth
from app.routes import audit_logs

# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
# The FastAPI app object represents the running web service. The title is
# displayed in the interactive API docs (Swagger / ReDoc).
app = FastAPI(title="ER Service Desk API")


# ---------------------------------------------------------------------------
# FastAPI Routes
# ---------------------------------------------------------------------------
# Load all router modules into the FastAPI application

# User management: accounts, profiles, roles, and admin operations
app.include_router(users.router)

# Ticket operations: creation, updates, assignment, and lifecycle management
app.include_router(tickets.router)

# Ticket comments: threaded discussion and staff/user communication
app.include_router(comments.router)

# File attachments: upload, retrieval, and metadata for ticket files
app.include_router(attachments.router)

# Authentication and authorization: login, tokens, and permission checks
app.include_router(auth.router)

# Audit logging: system events, user actions, and compliance tracking
app.include_router(audit_logs.router)


# ---------------------------------------------------------------------------
# Health check endpoint
# ---------------------------------------------------------------------------
# This lightweight endpoint allows load balancers, uptime monitors, and
# deployment scripts to verify that the API is running and responsive.
@app.get("/health")
def health_check():
    """
    Simple health check endpoint.

    Returns a static JSON payload indicating that the service is operational.
    Useful for Kubernetes probes, monitoring tools, and CI/CD validation.
    """
    return {"status": "ok"}
