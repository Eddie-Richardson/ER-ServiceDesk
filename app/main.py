# ER-ServiceDesk/app/main.py
# FastAPI application entrypoint

from fastapi import FastAPI

# Create FastAPI app with project title
app = FastAPI(title="ER Service Desk API")

@app.get("/health")
def health_check():
    # Simple health check endpoint
    return {"status": "ok"}
