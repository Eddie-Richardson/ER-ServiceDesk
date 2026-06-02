# ER-ServiceDesk/app/workers/workers.py
# RQ worker setup for processing background jobs

from redis import Redis
from rq import Queue, Worker
from app.core.config import settings

# Queues this worker will listen to
listen = ["default"]

# Redis connection used by RQ
redis_conn = Redis.from_url(settings.REDIS_URL)

if __name__ == "__main__":
    # Create queue instance
    q = Queue("default", connection=redis_conn)

    # Create and start the worker
    worker = Worker([q], connection=redis_conn)
    worker.work()
