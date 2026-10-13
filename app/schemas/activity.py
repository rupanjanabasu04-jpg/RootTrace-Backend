from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ActivityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    description: str
    created_at: datetime
