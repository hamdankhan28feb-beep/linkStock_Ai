from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.models.order import OrderStatus


class OrderItemCreate(BaseModel):
    product_id: UUID
    quantity: int


class OrderItemOut(BaseModel):
    id: UUID
    order_id: UUID
    product_id: UUID
    quantity: int
    unit_price: Decimal
    subtotal: Optional[float] = None
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    product_unit: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    items: List[OrderItemCreate]
    notes: Optional[str] = None


class OrderUpdate(BaseModel):
    status: Optional[OrderStatus] = None
    distributor_id: Optional[UUID] = None
    notes: Optional[str] = None


class OrderOut(BaseModel):
    id: UUID
    retailer_id: UUID
    distributor_id: Optional[UUID] = None
    status: OrderStatus
    total_amount: Decimal
    notes: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    items: List[OrderItemOut] = []
    retailer_name: Optional[str] = None
    retailer_area: Optional[str] = None
    retailer_lat: Optional[float] = None
    retailer_lon: Optional[float] = None

    model_config = {"from_attributes": True}


class OrderSummary(BaseModel):
    """Lightweight order summary for list views."""
    id: UUID
    retailer_id: UUID
    status: OrderStatus
    total_amount: Decimal
    created_at: datetime
    retailer_name: Optional[str] = None
    retailer_area: Optional[str] = None
    item_count: Optional[int] = None

    model_config = {"from_attributes": True}
