from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from .user import User
from .semester import Semester


class GroupBase(BaseModel):
    name: str
    description: Optional[str] = None
    semester_id: int


class GroupCreate(GroupBase):
    pass


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    semester_id: Optional[int] = None


class Group(GroupBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GroupWithRelations(Group):
    semester: Semester
    users: List[User]


class GroupWithStats(Group):
    semester: Semester
    user_count: int
    session_count: int
    total_bookings: int


class GroupList(BaseModel):
    groups: List[GroupWithStats]
    total: int


class GroupUserAdd(BaseModel):
    user_id: int