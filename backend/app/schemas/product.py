from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID
from decimal import Decimal


class ProductBase(BaseModel):
    name: str
    sku: str
    category: str
    description: Optional[str] = None
    unit_price: Decimal
    unit: str = "unit"
    image_url: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    unit_price: Optional[Decimal] = None
    unit: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: UUID
    is_active: bool
    created_at: datetime
    current_stock: Optional[int] = None        # Joined from inventory
    is_low_stock: Optional[bool] = None

    model_config = {"from_attributes": True}
