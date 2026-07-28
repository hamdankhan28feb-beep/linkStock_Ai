import uuid
from sqlalchemy import Column, Integer, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), unique=True, nullable=False)
    warehouse_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    quantity = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, nullable=False, default=50)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("quantity >= 0", name="ck_inventory_quantity_non_negative"),
        CheckConstraint("low_stock_threshold >= 0", name="ck_inventory_threshold_non_negative"),
    )

    # Relationships
    product = relationship("Product", back_populates="inventory")
    warehouse_user = relationship("User", back_populates="inventory_items")
    alerts = relationship("LowStockAlert", back_populates="inventory", cascade="all, delete-orphan")

    @property
    def is_low_stock(self) -> bool:
        return self.quantity <= self.low_stock_threshold

    def __repr__(self):
        return f"<Inventory product_id={self.product_id} qty={self.quantity}>"


class LowStockAlert(Base):
    __tablename__ = "low_stock_alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    inventory_id = Column(UUID(as_uuid=True), ForeignKey("inventory.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    current_quantity = Column(Integer, nullable=False)
    threshold = Column(Integer, nullable=False)
    is_read = Column(Integer, default=False)   # stored as int for pg compatibility
    triggered_at = Column(DateTime(timezone=True), server_default=func.now())
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    inventory = relationship("Inventory", back_populates="alerts")
    product = relationship("Product")

    def __repr__(self):
        return f"<LowStockAlert product_id={self.product_id} qty={self.current_quantity}>"
