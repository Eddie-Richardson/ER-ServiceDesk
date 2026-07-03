# ER-ServiceDesk/app/workers/worker.py
# RQ worker setup for processing background jobs
"""
Entrypoint for an RQ worker process. Listens on Redis-backed queues and
executes background jobs (notifications, async tasks, maintenance
routines) delegated by the API. Run directly: `python -m app.workers.worker`.
"""

from redis import Redis
from rq import Queue, Worker
from app.core.config import settings

listen = ["default"]
redis_conn = Redis.from_url(settings.REDIS_URL)

if __name__ == "__main__":
    q = Queue("default", connection=redis_conn)
    worker = Worker([q], connection=redis_conn)
    worker.work()
