from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ProjectMemberCreate(BaseModel):
    email: EmailStr
    role: str = Field(default="member", pattern="^(admin|member|viewer)$")


class ProjectMemberRoleUpdate(BaseModel):
    role: str = Field(pattern="^(admin|member|viewer)$")


class ProjectMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    role: str
    created_at: datetime
    updated_at: datetime


class ProjectMemberDetailResponse(ProjectMemberResponse):
    email: EmailStr
    full_name: str
