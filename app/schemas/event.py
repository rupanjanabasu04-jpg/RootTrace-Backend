from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventCreate(BaseModel):
    incident_id: UUID
    service_id: UUID | None = None
    event_type: str
    message: str
    occurred_at: datetime


class EventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    service_id: UUID | None
    event_type: str
    message: str
    occurred_at: datetime
    created_at: datetime
