from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import hashlib
import secrets

from ..database import Base

class CertificateTemplate(Base):
    """
    Tanúsítvány Template - Track-specifikus tanúsítvány sablon
    """
    __tablename__ = "certificate_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    track_id = Column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False)
    title = Column(String(255), nullable=False)  # "LFA PRE Football Certificate"
    description = Column(Text)
    design_template = Column(Text)  # HTML/CSS template
    validation_rules = Column(JSON, default=dict)  # Mi kell a kiállításhoz
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    track = relationship("Track", back_populates="certificate_template")
    issued_certificates = relationship("IssuedCertificate", back_populates="template")

    def __repr__(self):
        return f"<CertificateTemplate {self.title}>"

class IssuedCertificate(Base):
    """
    Kiállított Tanúsítványok - Hallgatók részére kiállított tanúsítványok
    """
    __tablename__ = "issued_certificates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    certificate_template_id = Column(UUID(as_uuid=True), ForeignKey("certificate_templates.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    unique_identifier = Column(String(100), nullable=False, unique=True)  # LFA-COACH-2024-A7B9C2
    issue_date = Column(DateTime, default=datetime.utcnow)
    completion_date = Column(DateTime)
    verification_hash = Column(String(256), nullable=False)  # SHA-256 hash for verification
    cert_metadata = Column(JSON, default=dict)  # Grades, completion stats, etc.
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revoked_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    template = relationship("CertificateTemplate", back_populates="issued_certificates")
    user = relationship("User")

    def __repr__(self):
        return f"<IssuedCertificate {self.unique_identifier}>"

    @staticmethod
    def generate_unique_identifier(track_code: str) -> str:
        """
        Generate unique certificate identifier
        Format: LFA-{TRACK_CODE}-{YEAR}-{RANDOM}
        """
        year = datetime.now().year
        random_suffix = secrets.token_hex(3).upper()  # 6 character hex
        return f"LFA-{track_code}-{year}-{random_suffix}"

    @staticmethod
    def generate_verification_hash(unique_id: str, user_id: str, issue_date: datetime) -> str:
        """
        Generate verification hash for certificate authenticity
        """
        data = f"{unique_id}:{user_id}:{issue_date.isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_authenticity(self) -> bool:
        """
        Verify certificate authenticity using hash
        """
        expected_hash = self.generate_verification_hash(
            self.unique_identifier,
            str(self.user_id),
            self.issue_date
        )
        return self.verification_hash == expected_hash

    @property
    def is_valid(self) -> bool:
        """Check if certificate is valid (not revoked and authentic)"""
        return not self.is_revoked and self.verify_authenticity()

    def revoke(self, reason: str = None):
        """Revoke the certificate"""
        self.is_revoked = True
        self.revoked_at = datetime.utcnow()
        self.revoked_reason = reason

    @property
    def display_id(self) -> str:
        """Display-friendly certificate ID"""
        return self.unique_identifier

    @property
    def verification_url(self) -> str:
        """Public verification URL"""
        return f"/certificates/{self.unique_identifier}/verify"