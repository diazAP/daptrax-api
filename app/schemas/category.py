from pydantic import BaseModel, Field
from uuid import UUID


class CategoryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int = 0


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    color_key: str | None = None
    icon_key: str | None = None
    sort_order: int

    class Config:
        from_attributes = True