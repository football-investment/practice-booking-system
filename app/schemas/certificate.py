"""
Certificate-related Pydantic schemas
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from uuid import UUID


# Certificate Template Schemas
class CertificateTemplateBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    title: str
    description: Optional[str] = None
    design_template: Optional[str] = None
    validation_rules: Optional[Dict[str, Any]] = None


class CertificateTemplateCreate(CertificateTemplateBase):
    track_id: UUID


class CertificateTemplateResponse(CertificateTemplateBase):
    id: UUID
    track_id: UUID
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# Issued Certificate Schemas
class IssuedCertificateBase(BaseModel):
    model_config = ConfigDict(extra='forbid')

    unique_identifier: str
    issue_date: datetime
    completion_date: Optional[datetime] = None
    is_revoked: bool = False


class CertificateResponse(IssuedCertificateBase):
    id: UUID
    track_name: str
    track_code: str
    final_grade: Optional[float] = None
    verification_url: str
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# Certificate Verification Schemas
class CertificateVerificationResponse(BaseModel):
    valid: bool
    certificate_id: Optional[str] = None
    user_name: Optional[str] = None
    track_name: Optional[str] = None
    track_code: Optional[str] = None
    issue_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    final_grade: Optional[str] = None
    duration_days: Optional[int] = None
    verification_hash: Optional[str] = None
    error: Optional[str] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None


# Certificate Analytics Schemas
class CertificateByTrackStats(BaseModel):
    track_name: str
    track_code: str
    count: int


class CertificateAnalyticsResponse(BaseModel):
    total_certificates_issued: int
    certificates_by_track: List[CertificateByTrackStats]
    revoked_certificates: int
    active_certificates: int


# Certificate Generation Request Schema
class CertificateGenerationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    track_progress_id: UUID


# Certificate Revocation Schema
class CertificateRevocationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')

    reason: str