# ER-ServiceDesk/desktop/formatting.py

"""
Small, shared display-formatting helpers, kept in their own module
(not owned by any specific dialog/tab) so multiple files can use them
without importing from each other and risking a circular dependency.
"""

from datetime import datetime


def format_timestamp(iso_string: str) -> str:
    """Formats an ISO datetime string for display, e.g. 'Aug 8, 2026 3:45 PM'. Returns the raw string unchanged if it can't be parsed."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %-d, %Y %-I:%M %p")
    except (ValueError, TypeError):
        return iso_string or ""
