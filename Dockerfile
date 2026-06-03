# ER-ServiceDesk/Dockerfile
# Docker image for running the ER Service Desk API
#
# This Dockerfile builds the runtime environment for the ER‑ServiceDesk API.
# It installs Python dependencies, copies the application code, and launches
# the FastAPI server using Uvicorn. Designed for local development and
# containerized deployment via Docker Compose.

FROM python:3.11-slim

# ---------------------------------------------------------------------------
# Working directory
# ---------------------------------------------------------------------------
# All application files will live under /app inside the container.
WORKDIR /app

# ---------------------------------------------------------------------------
# Install Python dependencies
# ---------------------------------------------------------------------------
# Copy only requirements first to leverage Docker layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---------------------------------------------------------------------------
# Copy application source code
# ---------------------------------------------------------------------------
COPY . .

# ---------------------------------------------------------------------------
# Start FastAPI with Uvicorn
# ---------------------------------------------------------------------------
# Exposes the API on port 8000 and binds to all interfaces.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
