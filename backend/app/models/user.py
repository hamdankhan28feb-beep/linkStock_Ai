import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Boolean, Enum as SAEnum, ForeignKey, Text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class UserRole(str, enum.Enum):
    warehouse = "warehouse"
    distributor = "distributor"
    retailer = "retailer"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(Text, nullable=False)
    role = Column(SAEnum(UserRole), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    location = relationship("Location", back_populates="user", uselist=False, cascade="all, delete-orphan")
    retailer_orders = relationship("Order", back_populates="retailer", foreign_keys="Order.retailer_id")
    distributor_orders = relationship("Order", back_populates="distributor", foreign_keys="Order.distributor_id")
    delivery_routes = relationship("DeliveryRoute", back_populates="distributor")
    inventory_items = relationship("Inventory", back_populates="warehouse_user")

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"
