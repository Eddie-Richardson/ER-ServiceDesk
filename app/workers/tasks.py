# ER-ServiceDesk/app/workers/tasks.py
# Example background task used by the worker system
#
# This module defines example background tasks for the ER‑ServiceDesk worker
# system. These tasks are executed asynchronously by the worker process and
# can be expanded to include email sending, notifications, cleanup jobs,
# scheduled maintenance, or any other non‑blocking operations.

# ---------------------------------------------------------------------------
# Example background task
# ---------------------------------------------------------------------------
def example_task(name: str):
    """
    Example background task.

    This task demonstrates how a worker‑executed function behaves. It accepts
    a name, performs lightweight processing, and returns a success message.
    In real implementations, this could trigger emails, logs, or async jobs.
    """
    return f"Hello {name}, your task ran successfully!"
