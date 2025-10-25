"""
🏮 GānCuju™️©️ License System Models
Marketing-oriented license progression system with cultural narratives
"""
import enum
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ..database import Base


class LicenseType(enum.Enum):
    """License specialization types"""
    COACH = "COACH"
    PLAYER = "PLAYER"
    INTERNSHIP = "INTERNSHIP"


class LicenseLevel(enum.Enum):
    """All license levels across specializations"""
    
    # COACH LEVELS - LFA System (8 levels)
    COACH_LFA_PRE_ASSISTANT = "coach_lfa_pre_assistant"
    COACH_LFA_PRE_HEAD = "coach_lfa_pre_head"
    COACH_LFA_YOUTH_ASSISTANT = "coach_lfa_youth_assistant"
    COACH_LFA_YOUTH_HEAD = "coach_lfa_youth_head"
    COACH_LFA_AMATEUR_ASSISTANT = "coach_lfa_amateur_assistant"
    COACH_LFA_AMATEUR_HEAD = "coach_lfa_amateur_head"
    COACH_LFA_PRO_ASSISTANT = "coach_lfa_pro_assistant"
    COACH_LFA_PRO_HEAD = "coach_lfa_pro_head"
    
    # PLAYER LEVELS - GānCuju™️©️ System (8 levels)
    PLAYER_BAMBOO_STUDENT = "player_bamboo_student"          # 🤍 Bambusz Tanítvány (Fehér)
    PLAYER_MORNING_DEW = "player_morning_dew"                # 💛 Hajnali Harmat (Sárga)
    PLAYER_FLEXIBLE_REED = "player_flexible_reed"            # 💚 Rugalmas Nád (Zöld)
    PLAYER_SKY_RIVER = "player_sky_river"                    # 💙 Égi Folyó (Kék)
    PLAYER_STRONG_ROOT = "player_strong_root"                # 🤎 Erős Gyökér (Barna)
    PLAYER_WINTER_MOON = "player_winter_moon"                # 🩶 Téli Hold (Sötétszürke)
    PLAYER_MIDNIGHT_GUARDIAN = "player_midnight_guardian"    # 🖤 Éjfél Őrzője (Fekete)
    PLAYER_DRAGON_WISDOM = "player_dragon_wisdom"           # ❤️ Sárkány Bölcsesség (Vörös)
    
    # INTERN LEVELS - IT Career System (5 levels)
    INTERN_JUNIOR = "intern_junior"                          # 🔰 Junior Intern
    INTERN_MID_LEVEL = "intern_mid_level"                    # 📈 Mid-level Intern
    INTERN_SENIOR = "intern_senior"                          # 🎯 Senior Intern
    INTERN_LEAD = "intern_lead"                              # 👑 Lead Intern
    INTERN_PRINCIPAL = "intern_principal"                    # 🚀 Principal Intern


class LicenseMetadata(Base):
    """License level metadata with marketing content and visual assets"""
    __tablename__ = "license_metadata"

    id = Column(Integer, primary_key=True, index=True)
    specialization_type = Column(String(20), nullable=False)  # COACH, PLAYER, INTERNSHIP
    level_code = Column(String(50), nullable=False)           # e.g., 'player_bamboo_student'
    level_number = Column(Integer, nullable=False)            # 1-8 for most, 1-5 for intern
    
    # Display Information
    title = Column(String(100), nullable=False)               # "Bambusz Tanítvány"
    title_en = Column(String(100))                            # "Bamboo Student"
    subtitle = Column(String(200))                            # "A rugalmasság első leckéi"
    color_primary = Column(String(7), nullable=False)         # "#F8F8FF"
    color_secondary = Column(String(7))                       # "#E6E6FA"
    icon_emoji = Column(String(10))                           # "🤍"
    icon_symbol = Column(String(50))                          # CSS class or symbol
    
    # Marketing Content
    marketing_narrative = Column(Text)                        # Rich marketing description
    cultural_context = Column(Text)                           # Cultural/historical context
    philosophy = Column(Text)                                 # Philosophical aspects
    
    # Visual Assets
    background_gradient = Column(String(200))                 # CSS gradient definition
    css_class = Column(String(50))                           # CSS class for styling
    image_url = Column(String(500))                          # Optional image asset
    
    # Requirements
    advancement_criteria = Column(JSON)                      # JSON structure of requirements
    time_requirement_hours = Column(Integer)                  # Minimum time requirement
    project_requirements = Column(JSON)                      # Project-based requirements
    evaluation_criteria = Column(JSON)                       # Evaluation criteria
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), 
                       onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "specialization_type": self.specialization_type,
            "level_code": self.level_code,
            "level_number": self.level_number,
            "title": self.title,
            "title_en": self.title_en,
            "subtitle": self.subtitle,
            "color_primary": self.color_primary,
            "color_secondary": self.color_secondary,
            "icon_emoji": self.icon_emoji,
            "icon_symbol": self.icon_symbol,
            "marketing_narrative": self.marketing_narrative,
            "cultural_context": self.cultural_context,
            "philosophy": self.philosophy,
            "background_gradient": self.background_gradient,
            "css_class": self.css_class,
            "image_url": self.image_url,
            "advancement_criteria": self.advancement_criteria,
            "time_requirement_hours": self.time_requirement_hours,
            "project_requirements": self.project_requirements,
            "evaluation_criteria": self.evaluation_criteria
        }


class UserLicense(Base):
    """Track user license progression for each specialization"""
    __tablename__ = "user_licenses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    specialization_type = Column(String(20), nullable=False)  # COACH, PLAYER, INTERNSHIP
    current_level = Column(Integer, nullable=False, default=1)
    max_achieved_level = Column(Integer, nullable=False, default=1)
    started_at = Column(DateTime, nullable=False)
    last_advanced_at = Column(DateTime)
    instructor_notes = Column(Text)                           # Instructor feedback/notes
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="licenses")
    progressions = relationship("LicenseProgression", back_populates="user_license", 
                               cascade="all, delete-orphan")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "specialization_type": self.specialization_type,
            "current_level": self.current_level,
            "max_achieved_level": self.max_achieved_level,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "last_advanced_at": self.last_advanced_at.isoformat() if self.last_advanced_at else None,
            "instructor_notes": self.instructor_notes
        }


class LicenseProgression(Base):
    """Track license advancement history"""
    __tablename__ = "license_progressions"

    id = Column(Integer, primary_key=True, index=True)
    user_license_id = Column(Integer, ForeignKey("user_licenses.id"), nullable=False)
    from_level = Column(Integer, nullable=False)
    to_level = Column(Integer, nullable=False)
    advanced_by = Column(Integer, ForeignKey("users.id"))     # Instructor who approved advancement
    advancement_reason = Column(Text)                         # Reason for advancement
    requirements_met = Column(Text)                           # Which requirements were satisfied
    advanced_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user_license = relationship("UserLicense", back_populates="progressions")
    instructor = relationship("User", foreign_keys=[advanced_by])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses"""
        return {
            "id": self.id,
            "user_license_id": self.user_license_id,
            "from_level": self.from_level,
            "to_level": self.to_level,
            "advanced_by": self.advanced_by,
            "advancement_reason": self.advancement_reason,
            "requirements_met": self.requirements_met,
            "advanced_at": self.advanced_at.isoformat() if self.advanced_at else None
        }


# Configure relationships after all models are defined
def configure_license_relationships():
    """Configure relationships between User and license models"""
    from .user import User
    
    # Add relationships to User model if not already present
    if not hasattr(User, 'licenses'):
        User.licenses = relationship("UserLicense", back_populates="user")


class LicenseSystemHelper:
    """Helper class for license system operations"""
    
    @staticmethod
    def get_specialization_max_level(specialization: str) -> int:
        """Get maximum level for a specialization"""
        max_levels = {
            "COACH": 8,
            "PLAYER": 8,
            "INTERNSHIP": 5
        }
        return max_levels.get(specialization, 1)
    
    @staticmethod
    def get_level_metadata(specialization: str, level: int) -> Optional[str]:
        """Get level code for specialization and level number"""
        level_maps = {
            "COACH": {
                1: LicenseLevel.COACH_LFA_PRE_ASSISTANT.value,
                2: LicenseLevel.COACH_LFA_PRE_HEAD.value,
                3: LicenseLevel.COACH_LFA_YOUTH_ASSISTANT.value,
                4: LicenseLevel.COACH_LFA_YOUTH_HEAD.value,
                5: LicenseLevel.COACH_LFA_AMATEUR_ASSISTANT.value,
                6: LicenseLevel.COACH_LFA_AMATEUR_HEAD.value,
                7: LicenseLevel.COACH_LFA_PRO_ASSISTANT.value,
                8: LicenseLevel.COACH_LFA_PRO_HEAD.value,
            },
            "PLAYER": {
                1: LicenseLevel.PLAYER_BAMBOO_STUDENT.value,
                2: LicenseLevel.PLAYER_MORNING_DEW.value,
                3: LicenseLevel.PLAYER_FLEXIBLE_REED.value,
                4: LicenseLevel.PLAYER_SKY_RIVER.value,
                5: LicenseLevel.PLAYER_STRONG_ROOT.value,
                6: LicenseLevel.PLAYER_WINTER_MOON.value,
                7: LicenseLevel.PLAYER_MIDNIGHT_GUARDIAN.value,
                8: LicenseLevel.PLAYER_DRAGON_WISDOM.value,
            },
            "INTERNSHIP": {
                1: LicenseLevel.INTERN_JUNIOR.value,
                2: LicenseLevel.INTERN_MID_LEVEL.value,
                3: LicenseLevel.INTERN_SENIOR.value,
                4: LicenseLevel.INTERN_LEAD.value,
                5: LicenseLevel.INTERN_PRINCIPAL.value,
            }
        }
        return level_maps.get(specialization, {}).get(level)
    
    @staticmethod
    def validate_advancement(current_level: int, target_level: int, max_level: int) -> tuple[bool, str]:
        """Validate if license advancement is possible"""
        if target_level <= current_level:
            return False, "Target level must be higher than current level"
        
        if target_level > current_level + 1:
            return False, "Can only advance one level at a time"
        
        if target_level > max_level:
            return False, f"Maximum level for this specialization is {max_level}"
        
        return True, "Advancement is valid"