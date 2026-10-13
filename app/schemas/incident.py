from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IncidentCreate(BaseModel):
    title: str
    description: str | None = None


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str | None
    status: str
    created_at: datetime
