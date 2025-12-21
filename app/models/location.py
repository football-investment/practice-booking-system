"""
📍 Location Model

Represents LFA Education Centers (CITIES) where campuses are located.
A Location is a city-level entity (e.g., Budapest, Budaörs).
Each Location can have multiple Campuses (venues).

Hierarchy:
  Location (City) → Multiple Campuses → Sessions held at Campus
  Instructor → Bound to Location (can teach at any campus in that location)

Example:
    Location: Budapest
      ├── Campus: Buda Campus
      └── Campus: Pest Campus
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class Location(Base):
    """LFA Education Center locations (city-level)"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Will be deprecated - use city as primary identifier
    city = Column(String(100), nullable=False, unique=True)  # Primary identifier for location
    postal_code = Column(String(20), nullable=True)  # ZIP/Postal code
    country = Column(String(100), nullable=False)
    venue = Column(String(200), nullable=True)  # DEPRECATED - will be moved to Campus model
    address = Column(String(500), nullable=True)  # General city address info
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campuses = relationship("Campus", back_populates="location", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Location(id={self.id}, city='{self.city}', country='{self.country}')>"
