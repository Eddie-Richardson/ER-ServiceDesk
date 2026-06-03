# ER-ServiceDesk/app/workers/workers.py
# RQ worker setup for processing background jobs
#
# This module configures and launches an RQ worker for the ER‑ServiceDesk
# application. The worker listens on one or more Redis-backed queues and
# processes background jobs such as notifications, async tasks, maintenance
# routines, or any non-blocking operations delegated by the API.

from redis import Redis
from rq import Queue, Worker
from app.core.config import settings

# ---------------------------------------------------------------------------
# Queue configuration
# ---------------------------------------------------------------------------
# The list of queue names this worker will listen to.
# Additional queues can be added as the system grows.
listen = ["default"]

# ---------------------------------------------------------------------------
# Redis connection
# ---------------------------------------------------------------------------
# Establish a Redis connection using the configured REDIS_URL.
# This connection is shared by all queues and workers.
redis_conn = Redis.from_url(settings.REDIS_URL)

# ---------------------------------------------------------------------------
# Worker startup
# ---------------------------------------------------------------------------
# When executed directly, this script initializes the queue and starts
# an RQ worker that continuously listens for and processes jobs.
if __name__ == "__main__":
    # Create a queue instance bound to the Redis connection
    q = Queue("default", connection=redis_conn)

    # Create and start the worker process
    worker = Worker([q], connection=redis_conn)
    worker.work()
