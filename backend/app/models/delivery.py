import uuid
import enum
from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Text, Enum as SAEnum, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class RouteStatus(str, enum.Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"


class StopStatus(str, enum.Enum):
    pending = "pending"
    completed = "completed"
    skipped = "skipped"


class DeliveryRoute(Base):
    """Represents one AI-clustered delivery batch (one cluster = one route)."""
    __tablename__ = "delivery_routes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    distributor_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    name = Column(String(200), nullable=True)          # Auto-generated, e.g. "Cluster A - North Karachi"
    cluster_label = Column(Integer, nullable=False)    # DBSCAN label (0, 1, 2, …; -1 = noise/solo)
    status = Column(SAEnum(RouteStatus), nullable=False, default=RouteStatus.pending)

    # Depot (distributor warehouse start location)
    depot_latitude = Column(Float, nullable=True)
    depot_longitude = Column(Float, nullable=True)
    depot_address = Column(Text, nullable=True)

    # OR-Tools output summary
    total_distance_km = Column(Float, nullable=True)
    total_stops = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    distributor = relationship("User", back_populates="delivery_routes")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan", order_by="RouteStop.stop_sequence")

    def __repr__(self):
        return f"<DeliveryRoute cluster={self.cluster_label} status={self.status}>"


class RouteStop(Base):
    """Each individual retailer delivery stop within a DeliveryRoute."""
    __tablename__ = "route_stops"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    route_id = Column(UUID(as_uuid=True), ForeignKey("delivery_routes.id", ondelete="CASCADE"), nullable=False, index=True)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id", ondelete="RESTRICT"), nullable=False, unique=True)
    retailer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    # OR-Tools assigns sequence
    stop_sequence = Column(Integer, nullable=False, default=0)

    # Denormalized for fast map rendering
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(Text, nullable=True)
    retailer_name = Column(String(100), nullable=True)

    # Stop metadata
    order_total = Column(Numeric(12, 2), nullable=True)
    status = Column(SAEnum(StopStatus), nullable=False, default=StopStatus.pending)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    route = relationship("DeliveryRoute", back_populates="stops")
    order = relationship("Order", back_populates="route_stop")
    retailer = relationship("User")

    def __repr__(self):
        return f"<RouteStop seq={self.stop_sequence} status={self.status}>"
