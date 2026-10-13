from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DeploymentCreate(BaseModel):
    incident_id: UUID
    service_id: UUID
    change_type: str
    version: str | None = None
    description: str | None = None
    occurred_at: datetime


class DeploymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    service_id: UUID
    change_type: str
    version: str | None
    description: str | None
    occurred_at: datetime
    created_at: datetime

