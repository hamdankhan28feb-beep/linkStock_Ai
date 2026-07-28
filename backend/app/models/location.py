import uuid
from sqlalchemy import Column, String, Float, ForeignKey, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    address = Column(Text, nullable=True)
    area = Column(String(100), nullable=True)   # e.g. "Gulshan-e-Iqbal"
    city = Column(String(100), default="Karachi")
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="location")

    def __repr__(self):
        return f"<Location user_id={self.user_id} ({self.latitude}, {self.longitude})>"
