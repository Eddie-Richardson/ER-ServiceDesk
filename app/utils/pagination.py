# ER-ServiceDesk/app/utils/pagination.py
# Pagination + serialization helpers
"""
Reusable pagination helper for SQLAlchemy ORM queries, plus a plain-dict
serializer for model instances. Ported from InventoryHub and generalized
for use across any router in the app, not just inventory.
"""

from math import ceil
from typing import Any, Dict
from sqlalchemy.orm import Query
from sqlalchemy import func


def serialize_model(obj) -> Dict[str, Any]:
    """
    Convert a SQLAlchemy model instance into a plain dictionary.

    Args:
        obj: SQLAlchemy model instance.

    Returns:
        A dict of column_name -> value, excluding SQLAlchemy internals.
    """
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def paginate_query(query: Query, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy ORM query and return page metadata + items.

    Args:
        query: SQLAlchemy ORM query to paginate.
        limit: Maximum number of items to return (must be > 0).
        offset: Number of items to skip (must be >= 0).

    Returns:
        A dict with total/limit/offset/count/items/total_pages/current_page/
        next_page/previous_page.

    Raises:
        ValueError: If limit is not positive or offset is negative.
    """
    if limit <= 0:
        raise ValueError("limit must be a positive integer")
    if offset < 0:
        raise ValueError("offset must be a non-negative integer")

    count_query = query.order_by(None)
    total = count_query.session.execute(
        count_query.statement.with_only_columns(func.count())
    ).scalar()

    items = query.limit(limit).offset(offset).all()
    count = len(items)

    total_pages = ceil(total / limit) if total > 0 else 0
    current_page = (offset // limit) + 1 if total > 0 else 1

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "count": count,
        "items": [serialize_model(item) for item in items],
        "total_pages": total_pages,
        "current_page": current_page,
        "next_page": (offset + limit) < total,
        "previous_page": offset > 0,
    }
