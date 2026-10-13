from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AttachmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    task_id: UUID
    uploaded_by: UUID
    original_filename: str
    content_type: str
    file_size: int
    created_at: datetime
