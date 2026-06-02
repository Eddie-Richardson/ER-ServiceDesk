# ER-ServiceDesk/app/workers/tasks.py
# Example background task used by the worker system

def example_task(name: str):
    # Return a simple success message for the task
    return f"Hello {name}, your task ran successfully!"
