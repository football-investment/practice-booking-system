from pydantic import BaseModel, EmailStr, ConfigDict, field_serializer
from typing import Optional, List
from datetime import datetime
from ..models.user import UserRole
from ..models.specialization import SpecializationType


class UserBase(BaseModel):
    name: str
    nickname: Optional[str] = None
    email: EmailStr
    role: UserRole = UserRole.STUDENT
    is_active: bool = True


class UserCreate(UserBase):
    password: str
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    medical_notes: Optional[str] = None
    position: Optional[str] = None
    specialization: Optional[str] = None
    onboarding_completed: Optional[bool] = False
    payment_verified: Optional[bool] = False
    parental_consent: Optional[bool] = False
    parental_consent_by: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserUpdateSelf(BaseModel):
    name: Optional[str] = None
    nickname: Optional[str] = None
    email: Optional[EmailStr] = None
    onboarding_completed: Optional[bool] = None
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    medical_notes: Optional[str] = None
    interests: Optional[str] = None  # JSON string of interests array
    position: Optional[str] = None  # Football position
    specialization: Optional[str] = None  # Player/Coach/Internship
    nda_accepted: Optional[bool] = None
    nda_ip_address: Optional[str] = None
    parental_consent: Optional[bool] = None
    parental_consent_by: Optional[str] = None


class User(UserBase):
    id: int
    onboarding_completed: Optional[bool] = False
    phone: Optional[str] = None
    emergency_contact: Optional[str] = None
    emergency_phone: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    medical_notes: Optional[str] = None
    interests: Optional[str] = None  # JSON string of interests array
    position: Optional[str] = None  # Football position
    specialization: Optional[str] = None  # Player/Coach/Internship track
    payment_verified: Optional[bool] = False
    payment_verified_at: Optional[datetime] = None
    payment_verified_by: Optional[int] = None
    nda_accepted: Optional[bool] = False
    nda_accepted_at: Optional[datetime] = None
    nda_ip_address: Optional[str] = None
    parental_consent: Optional[bool] = False
    parental_consent_at: Optional[datetime] = None
    parental_consent_by: Optional[str] = None
    created_at: Optional[datetime] = None  # Make optional for legacy data
    updated_at: Optional[datetime] = None
    created_by: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer('specialization')
    def serialize_specialization(self, value, _info):
        """Convert SpecializationType enum to string"""
        if value is None:
            return None
        if isinstance(value, SpecializationType):
            return value.value
        return value


class UserWithStats(User):
    total_bookings: int
    completed_sessions: int
    feedback_count: int


class UserList(BaseModel):
    users: List[User]
    total: int
    page: int
    size: int