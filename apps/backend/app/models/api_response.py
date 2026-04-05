from __future__ import annotations

from datetime import datetime
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiMeta(BaseModel):
    version: str = "v2"
    mode: str
    path: str
    correlation_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ApiError(BaseModel):
    code: str
    message: str
    details: Optional[object] = None


class ApiResponse(BaseModel, Generic[T]):
    meta: ApiMeta
    data: T


class Pagination(BaseModel):
    total: int
    skip: int = 0
    limit: int = 0


class PaginatedResponse(BaseModel, Generic[T]):
    meta: ApiMeta
    data: List[T]
    pagination: Pagination
