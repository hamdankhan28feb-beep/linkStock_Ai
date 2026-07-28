import uuid
import enum
from sqlalchemy import Column, String, Numeric, Text, ForeignKey, DateTime, Integer, Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class OrderStatus(str, enum.Enum):
    pending = "pending"
    confirmed = "confirmed"
    clustered = "clustered"
    in_transit = "in_transit"
    delivered = "delivered"
    cancelled = "cancelled"


class Order(Base):
    __tablename__ = "orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    retailer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(SAEnum(OrderStatus), nullable=False, default=OrderStatus.pending)
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    retailer = relationship("User", back_populates="retailer_orders", foreign_keys=[retailer_id])
    distributor = relationship("User", back_populates="distributor_orders", foreign_keys=[distributor_id])
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")
    route_stop = relationship("RouteStop", back_populates="order", uselist=False)

    def __repr__(self):
        return f"<Order {self.id} status={self.status}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="RESTRICT"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)  # snapshot at order time

    # Relationships
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")

    @property
    def subtotal(self):
        return self.quantity * float(self.unit_price)

    def __repr__(self):
        return f"<OrderItem order_id={self.order_id} product_id={self.product_id} qty={self.quantity}>"
