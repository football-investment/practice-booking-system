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
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

from ..database import Base


class LocationType(enum.Enum):
    """Location capability level for semester types"""
    PARTNER = "PARTNER"  # Can host: Tournament + Mini Season only
    CENTER = "CENTER"    # Can host: Tournament + Mini Season + Academy Season


class Location(Base):
    """LFA Education Center locations (city-level)"""
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)  # Will be deprecated - use city as primary identifier
    city = Column(String(100), nullable=False, unique=True)  # Primary identifier for location
    postal_code = Column(String(20), nullable=True)  # ZIP/Postal code
    country = Column(String(100), nullable=False)
    country_code = Column(String(2), nullable=True)  # ISO country code (e.g., HU, AT, SK)
    location_code = Column(String(10), nullable=True, unique=True)  # Unique location code (e.g., BDPST, VIE)
    venue = Column(String(200), nullable=True)  # DEPRECATED - will be moved to Campus model
    address = Column(String(500), nullable=True)  # General city address info
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # NEW: Location type determines what semester types can be hosted
    location_type = Column(
        SQLEnum(LocationType, name='locationtype', create_constraint=True),
        nullable=False,
        default=LocationType.PARTNER,
        comment="Location capability: PARTNER (Tournament+Mini only) or CENTER (all types)"
    )

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    campuses = relationship("Campus", back_populates="location", cascade="all, delete-orphan")

    @property
    def display_name(self) -> str:
        """
        Returns formatted location name with flag emoji and country code.
        Format: 🇭🇺 HU - Budapest
        """
        flag = self.get_country_flag()
        if self.country_code:
            return f"{flag} {self.country_code} - {self.city}"
        return f"{flag} {self.city}"

    def get_country_flag(self) -> str:
        """
        Returns flag emoji for the country code.
        Uses Unicode regional indicator symbols.
        """
        if not self.country_code or len(self.country_code) != 2:
            return "🌍"  # Default globe emoji

        # Convert country code to flag emoji (e.g., HU -> 🇭🇺)
        code_points = [ord(char) + 127397 for char in self.country_code.upper()]
        return chr(code_points[0]) + chr(code_points[1])

    def __repr__(self):
        return f"<Location(id={self.id}, city='{self.city}', country='{self.country}')>"
