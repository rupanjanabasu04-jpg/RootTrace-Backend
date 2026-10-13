from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    project_id: UUID | None
    task_id: UUID | None
    notification_type: str
    title: str
    message: str
    is_read: bool
    created_at: datetime
