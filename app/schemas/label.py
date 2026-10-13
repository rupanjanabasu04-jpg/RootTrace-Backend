from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LabelCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class LabelUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class LabelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    name: str
    created_at: datetime
