from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DependencyCreate(BaseModel):
    source_service_id: UUID
    target_service_id: UUID
    dependency_type: str = "runtime"


class DependencyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_service_id: UUID
    target_service_id: UUID
    dependency_type: str

