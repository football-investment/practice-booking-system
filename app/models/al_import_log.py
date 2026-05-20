"""ALImportLog — one row per admin import operation."""
import enum
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..database import Base


class ImportStatus(enum.Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    ERROR   = "error"


class ALImportLog(Base):
    __tablename__ = "al_import_logs"

    id               = Column(Integer, primary_key=True, index=True)
    operator_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    spec             = Column(String(64), nullable=False)
    status           = Column(SQLEnum(ImportStatus, native_enum=False), nullable=False)
    completed_at     = Column(DateTime(timezone=True), nullable=False,
                              default=lambda: datetime.now(timezone.utc))
    files_submitted  = Column(Integer, nullable=False, default=0)
    files_ok         = Column(Integer, nullable=False, default=0)
    files_skipped    = Column(Integer, nullable=False, default=0)
    files_error      = Column(Integer, nullable=False, default=0)
    quizzes_created  = Column(Integer, nullable=False, default=0)
    questions_created = Column(Integer, nullable=False, default=0)
    options_fixed    = Column(Integer, nullable=False, default=0)
    options_variant  = Column(Integer, nullable=False, default=0)
    options_distractor = Column(Integer, nullable=False, default=0)
    details_json     = Column(Text, nullable=False, default="[]")

    operator = relationship("User", foreign_keys=[operator_id])
