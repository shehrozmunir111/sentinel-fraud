from pydantic import BaseModel, ConfigDict
from typing import Generic, TypeVar, List, Optional

T = TypeVar('T')

class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class PaginationParams(BaseModel):
    page: int = 1
    limit: int = 20
    sort_by: Optional[str] = None
    sort_order: Optional[str] = "desc"

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int