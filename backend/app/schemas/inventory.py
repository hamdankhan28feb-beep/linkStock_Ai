from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class InventoryBase(BaseModel):
    quantity: int
    low_stock_threshold: int = 50


class InventoryCreate(InventoryBase):
    product_id: UUID
    warehouse_user_id: Optional[UUID] = None


class InventoryUpdate(BaseModel):
    quantity: Optional[int] = None
    low_stock_threshold: Optional[int] = None


class InventoryAdjust(BaseModel):
    """For manual stock adjustments (+/- delta)."""
    delta: int      # positive = restock, negative = manual deduction
    reason: Optional[str] = None


class InventoryOut(BaseModel):
    id: UUID
    product_id: UUID
    warehouse_user_id: Optional[UUID] = None
    quantity: int
    low_stock_threshold: int
    is_low_stock: bool
    updated_at: Optional[datetime] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_category: Optional[str] = None
    product_unit: Optional[str] = None

    model_config = {"from_attributes": True}


class LowStockAlertOut(BaseModel):
    id: UUID
    inventory_id: UUID
    product_id: UUID
    current_quantity: int
    threshold: int
    is_read: bool
    triggered_at: datetime
    resolved_at: Optional[datetime] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None

    model_config = {"from_attributes": True}
