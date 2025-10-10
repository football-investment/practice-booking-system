from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Float, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from ..database import Base

class Track(Base):
    """
    Szakirány (Track) - Legfelső szintű oktatási egység
    Pl: LFA Internship, Coach, GānCuju
    """
    __tablename__ = "tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)  # "LFA Internship"
    code = Column(String(50), nullable=False, unique=True)  # "INT"
    description = Column(Text)
    duration_semesters = Column(Integer, default=1)
    prerequisites = Column(JSON, default=dict)  # Más track-ek előfeltételei
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    modules = relationship("Module", back_populates="track", cascade="all, delete-orphan")
    certificate_template = relationship("CertificateTemplate", back_populates="track", uselist=False)
    user_progresses = relationship("UserTrackProgress", back_populates="track")

    def __repr__(self):
        return f"<Track {self.name} ({self.code})>"

    @property
    def total_modules(self):
        """Total number of modules in this track"""
        return len(self.modules)

    @property
    def mandatory_modules(self):
        """Number of mandatory modules"""
        return len([m for m in self.modules if m.is_mandatory])

class Module(Base):
    """
    Modul - Track-en belüli tanulási egység
    Pl: "Taktikai Alapok", "Megyeri Gyakorlat"
    """
    __tablename__ = "modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False)
    semester_id = Column(UUID(as_uuid=True), ForeignKey("semesters.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text)
    order_in_track = Column(Integer, default=0)
    learning_objectives = Column(JSON, default=list)
    estimated_hours = Column(Integer, default=0)
    is_mandatory = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    track = relationship("Track", back_populates="modules")
    semester = relationship("Semester")
    components = relationship("ModuleComponent", back_populates="module", cascade="all, delete-orphan")
    user_progresses = relationship("UserModuleProgress", back_populates="module")

    def __repr__(self):
        return f"<Module {self.name} in {self.track.name}>"

    @property
    def total_components(self):
        """Total number of components in this module"""
        return len(self.components)

    @property
    def mandatory_components(self):
        """Number of mandatory components"""
        return len([c for c in self.components if c.is_mandatory])

class ModuleComponent(Base):
    """
    Modul Komponens - Konkrét tanulási elemek
    Típusok: theory, quiz, project, assignment, video
    """
    __tablename__ = "module_components"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("modules.id"), nullable=False)
    type = Column(String(50), nullable=False)  # 'theory', 'quiz', 'project', 'assignment', 'video'
    name = Column(String(255), nullable=False)
    description = Column(Text)
    order_in_module = Column(Integer, default=0)
    estimated_minutes = Column(Integer, default=0)
    is_mandatory = Column(Boolean, default=True)
    component_data = Column(JSON, default=dict)  # Type-specific data
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    module = relationship("Module", back_populates="components")

    def __repr__(self):
        return f"<ModuleComponent {self.name} ({self.type})>"

    @property
    def estimated_hours(self):
        """Convert minutes to hours"""
        return round(self.estimated_minutes / 60, 1) if self.estimated_minutes else 0