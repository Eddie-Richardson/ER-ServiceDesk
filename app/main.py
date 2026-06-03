# ER-ServiceDesk/app/main.py
# FastAPI application entrypoint
#
# This module serves as the main entrypoint for the ER‑ServiceDesk API.
# It initializes the FastAPI application, configures global settings such
# as the project title, and exposes core routes like the health check
# endpoint used for uptime monitoring and deployment validation.

from fastapi import FastAPI

# ---------------------------------------------------------------------------
# FastAPI application instance
# ---------------------------------------------------------------------------
# The FastAPI app object represents the running web service. The title is
# displayed in the interactive API docs (Swagger / ReDoc).
app = FastAPI(title="ER Service Desk API")

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
