"""
app/shared/responses.py
────────────────────────
Standardised Pydantic response models used across all routers.

Before: every endpoint returned a bare dict with inconsistent shapes.
After:  all list endpoints return PagedResponse[T], all single-item
        endpoints return the model directly or ApiResponse[T].
"""

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List, Any

T = TypeVar("T")


class PagedResponse(BaseModel, Generic[T]):
    """Standard response for all list/grid endpoints."""
    count:      int
    list:       List[T]
    parameters: Optional[Any] = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard wrapper for single-item or command responses."""
    data:    Optional[T]   = None
    success: bool          = True
    message: Optional[str] = None


class ErrorDetail(BaseModel):
    field:   Optional[str] = None
    message: str


class ErrorResponse(BaseModel):
    success: bool            = False
    message: str
    errors:  List[ErrorDetail] = []
