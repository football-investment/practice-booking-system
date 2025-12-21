"""
Campus Model - Venues within a Location (City)

A Location represents a city (e.g., Budapest, Budaörs)
A Campus represents a specific venue within that city (e.g., Buda Campus, Pest Campus)

Hierarchy:
  Location (City) → Multiple Campuses
  Instructor → Bound to Location (can teach at any campus in that location)
  Session → Held at specific Campus
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class Campus(Base):
    """
    Campus/Venue model - specific facility within a location
    """
    __tablename__ = "campuses"

    id = Column(Integer, primary_key=True, index=True)

    # Foreign key to parent location (city)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="CASCADE"), nullable=False)

    # Campus details
    name = Column(String, nullable=False)  # e.g., "Buda Campus", "Main Field"
    venue = Column(String, nullable=True)  # Additional venue info if needed
    address = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    location = relationship("Location", back_populates="campuses")
    # sessions = relationship("Session", back_populates="campus")  # TODO: Add when migrating sessions
