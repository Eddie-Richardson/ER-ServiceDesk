# ER-ServiceDesk/app/workers/scheduler.py
# Registers recurring background jobs (RQ has no built-in scheduling of its own).
"""
Entrypoint for registering recurring jobs with rq-scheduler.

RQ itself only runs jobs that get explicitly enqueued -- it has no concept
of "run this every N seconds" on its own. rq-scheduler adds that on top:
this script registers the recurring jobs once, and a *separate* running
process (`rqscheduler`, installed as part of the rq-scheduler package)
is what actually enqueues them on schedule for the regular RQ worker
(app/workers/worker.py) to pick up and run.

Run this once (it's idempotent -- re-running just replaces the existing
scheduled job rather than duplicating it) whenever the schedule itself
changes. In production this would run once at deploy time; for local dev,
run it manually after starting Redis and before starting the scheduler
process.

To run the full stack locally, you need three things running:
    1. Redis                         (already in docker-compose.yml)
    2. python -m app.workers.scheduler   (registers the job -- run once)
    3. rqscheduler                   (actually triggers it on schedule)
    4. python -m app.workers.worker      (executes the enqueued jobs)
"""

from redis import Redis
from rq_scheduler import Scheduler
from datetime import datetime, timezone

from app.core.config import settings
from app.workers.tasks import poll_inbound_email

INBOUND_EMAIL_POLL_INTERVAL_SECONDS = 60

if __name__ == "__main__":
    redis_conn = Redis.from_url(settings.REDIS_URL)
    scheduler = Scheduler(queue_name="default", connection=redis_conn)

    # Clear any previously-scheduled instance of this job before
    # re-registering, so re-running this script doesn't stack up
    # duplicate recurring jobs.
    for job in scheduler.get_jobs():
        if job.func_name == "app.workers.tasks.poll_inbound_email":
            scheduler.cancel(job)

    scheduler.schedule(
        scheduled_time=datetime.now(timezone.utc),
        func=poll_inbound_email,
        interval=INBOUND_EMAIL_POLL_INTERVAL_SECONDS,
        repeat=None,  # None = repeat forever
    )

    print(
        f"Scheduled poll_inbound_email to run every "
        f"{INBOUND_EMAIL_POLL_INTERVAL_SECONDS}s. Make sure `rqscheduler` "
        f"and the worker (app.workers.worker) are also running."
    )
