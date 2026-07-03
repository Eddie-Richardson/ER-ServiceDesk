# ER-ServiceDesk/app/workers/tasks.py
# Example background task used by the worker system
"""
Placeholder background task demonstrating the worker-executed function
signature. Real tasks (emails, notifications, cleanup jobs) follow this
same pattern.
"""

def example_task(name: str):
    """
    Run a trivial example task.

    Args:
        name: Name to greet.

    Returns:
        A success message string.
    """
    return f"Hello {name}, your task ran successfully!"
