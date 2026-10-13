from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    user_id: UUID
    content: str
    created_at: datetime
    updated_at: datetime
