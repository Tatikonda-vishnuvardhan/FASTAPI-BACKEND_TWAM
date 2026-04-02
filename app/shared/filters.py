"""
app/shared/filters.py
─────────────────────
Single source of truth for filter/sort/pagination logic.

Previously COMPARISON_MAP was copy-pasted into every repository file.
All repositories now import apply_filters() and apply_ordering() from here.
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Query
from sqlalchemy import asc, desc


# ── Comparison operators ───────────────────────────────────────────────────────

COMPARISON_MAP: Dict[str, Any] = {
    "eq":         lambda col, val: col == val,
    "neq":        lambda col, val: col != val,
    "contains":   lambda col, val: col.ilike(f"%{val}%"),
    "startswith": lambda col, val: col.ilike(f"{val}%"),
    "endswith":   lambda col, val: col.ilike(f"%{val}"),
    "gt":         lambda col, val: col > val,
    "gte":        lambda col, val: col >= val,
    "lt":         lambda col, val: col < val,
    "lte":        lambda col, val: col <= val,
    "in":         lambda col, val: col.in_([v.strip() for v in str(val).split(",") if v.strip()]),
}


# ── Core helpers ───────────────────────────────────────────────────────────────

def apply_filters(query: Query, model, filters: Optional[List[dict]]) -> Query:
    """
    Apply a list of filter dicts to a SQLAlchemy query.
    Each dict has keys: property, comparison (default "eq"), value.
    Skips any filter whose property doesn't exist on the model.
    """
    if not filters:
        return query
    for f in filters:
        prop       = f.get("property")
        comparison = f.get("comparison", "eq").lower()
        value      = f.get("value")
        col        = getattr(model, prop, None)
        op         = COMPARISON_MAP.get(comparison)
        if col is not None and op is not None and value is not None:
            query = query.filter(op(col, value))
    return query


def apply_ordering(
    query: Query,
    model,
    order_property: Optional[str],
    order_ascending: Optional[bool],
) -> Query:
    """Apply ORDER BY to a query based on property name and direction."""
    if not order_property:
        return query
    col = getattr(model, order_property, None)
    if col is None:
        return query
    return query.order_by(asc(col) if order_ascending is not False else desc(col))


def apply_pagination(
    query: Query,
    page_index: Optional[int],
    page_size: Optional[int],
) -> Query:
    """Apply LIMIT/OFFSET pagination. Skips if either value is missing/zero."""
    if page_index and page_size and page_index > 0 and page_size > 0:
        query = query.offset((page_index - 1) * page_size).limit(page_size)
    return query


def build_paged_response(total: int, rows: list, page_index: Optional[int] = None,
                         page_size: Optional[int] = None) -> dict:
    """Standard paged response envelope used across all list endpoints."""
    return {
        "count":      total,
        "list":       rows,
        "parameters": None,
    }