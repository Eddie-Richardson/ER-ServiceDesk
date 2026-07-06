# ER-ServiceDesk/app/workers/queue.py
# Shared RQ queue connection for enqueueing background jobs from services.
"""
Small helper so any part of the app (service layer, routes, etc.) can
enqueue a background job without each caller reconnecting to Redis by hand.
"""

from redis import Redis
from rq import Queue

from app.core.config import settings


def get_queue() -> Queue:
    """
    Return the shared "default" RQ queue, connected via settings.REDIS_URL.

    A fresh Queue object is returned each call (Redis connections are
    cheap/pooled under the hood), so callers don't need to worry about
    holding a long-lived reference.
    """
    return Queue("default", connection=Redis.from_url(settings.REDIS_URL))
