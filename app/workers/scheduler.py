# ER-ServiceDesk/app/workers/scheduler.py
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
from app.db.session import SessionLocal
from app.services.system_setting_service import system_setting_service
from app.workers.tasks import poll_inbound_email, archive_inactive_customers

DEFAULT_INBOUND_EMAIL_POLL_INTERVAL_SECONDS = 60
ARCHIVE_INACTIVE_CUSTOMERS_INTERVAL_SECONDS = 86400  # once daily -- not time-sensitive; the threshold itself (how many months of inactivity) is the part that's configurable via SystemSetting, read fresh by the task on every run

if __name__ == "__main__":
    redis_conn = Redis.from_url(settings.REDIS_URL)
    scheduler = Scheduler(queue_name="default", connection=redis_conn)

    # Read live from SystemSetting (editable in Settings -> System
    # Settings), falling back to the old hardcoded default if it's
    # never been set. Unlike record_lock_service's timeout (re-read on
    # every acquire, so a change is instant), this only takes effect
    # the NEXT time this script runs -- which is every time the
    # scheduler container restarts (docker-compose.yml's own
    # restart: unless-stopped), since rq-scheduler's own interval is
    # fixed at registration and doesn't get re-checked afterward. An
    # admin wanting an immediate change can run
    # `docker-compose restart scheduler` to force that.
    db = SessionLocal()
    try:
        poll_interval_seconds = system_setting_service.get_int(
            db, "inbound_email_poll_interval_seconds", DEFAULT_INBOUND_EMAIL_POLL_INTERVAL_SECONDS
        )
    finally:
        db.close()

    # Clear any previously-scheduled instance of this job before
    # re-registering, so re-running this script doesn't stack up
    # duplicate recurring jobs.
    for job in scheduler.get_jobs():
        if job.func_name == "app.workers.tasks.poll_inbound_email":
            scheduler.cancel(job)

    scheduler.schedule(
        scheduled_time=datetime.now(timezone.utc),
        func=poll_inbound_email,
        interval=poll_interval_seconds,
        repeat=None,  # None = repeat forever
    )

    print(
        f"Scheduled poll_inbound_email to run every "
        f"{poll_interval_seconds}s. Make sure `rqscheduler` "
        f"and the worker (app.workers.worker) are also running."
    )

    for job in scheduler.get_jobs():
        if job.func_name == "app.workers.tasks.archive_inactive_customers":
            scheduler.cancel(job)

    scheduler.schedule(
        scheduled_time=datetime.now(timezone.utc),
        func=archive_inactive_customers,
        interval=ARCHIVE_INACTIVE_CUSTOMERS_INTERVAL_SECONDS,
        repeat=None,
    )

    print(
        f"Scheduled archive_inactive_customers to run every "
        f"{ARCHIVE_INACTIVE_CUSTOMERS_INTERVAL_SECONDS}s."
    )
