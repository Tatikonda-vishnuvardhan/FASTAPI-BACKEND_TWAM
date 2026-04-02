from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class CategoryCreate(BaseModel):
    name:             Optional[str]  = None
    description:      Optional[str]  = None
    about:            Optional[str]  = None
    url:              Optional[str]  = None
    displayOrder:     Optional[int]  = None
    parentCategoryId: Optional[int]  = None
    groupCategoryId:  Optional[bool] = None   # auto-set in repository
    isActive:         Optional[bool] = True   # default active
    userProfileId:    Optional[str]  = None
    categoryImage:    Optional[str]  = None


class CategoryUpdate(BaseModel):
    name:             Optional[str]  = None
    description:      Optional[str]  = None
    about:            Optional[str]  = None
    url:              Optional[str]  = None
    displayOrder:     Optional[int]  = None
    parentCategoryId: Optional[int]  = None
    groupCategoryId:  Optional[bool] = None   # auto-set in repository
    isActive:         Optional[bool] = True   # default active
    categoryImage:    Optional[str]  = None


class CategoryResponse(BaseModel):
    categoryId:         int
    name:               Optional[str]      = None
    description:        Optional[str]      = None
    about:              Optional[str]      = None
    url:                Optional[str]      = None
    displayOrder:       Optional[int]      = None
    parentCategoryId:   Optional[int]      = None
    parentCategoryName: Optional[str]      = None
    groupCategoryId:    Optional[bool]     = None
    isActive:           Optional[bool]     = None
    categoryImage:      Optional[str]      = None
    createdDate:        Optional[datetime] = None
    modifiedDate:       Optional[datetime] = None

    class Config:
        from_attributes = True


class CategoryListResponse(BaseModel):
    count:      int
    list:       List[CategoryResponse]
    parameters: Optional[Any] = None


# ── Menu tree (user-facing) ───────────────────────────────────────────────────

class CategoryMenu(BaseModel):
    categoryId:       int
    name:             Optional[str]  = None
    url:              Optional[str]  = None
    about:            Optional[str]  = None
    parentCategoryId: Optional[int]  = None
    groupCategoryId:  Optional[bool] = None
    children:         List["CategoryMenu"] = []


CategoryMenu.model_rebuild()


class CategoryMenuResponse(BaseModel):
    categories: List[CategoryMenu]


# ── Category product counts (user-facing widget) ──────────────────────────────

class CategoryProductCount(BaseModel):
    categoryId: int
    count:      int


# ── GetCategory list query (POST /GetCategory) ────────────────────────────────

class GetCategoryRequest(BaseModel):
    roleId: Optional[int] = 0