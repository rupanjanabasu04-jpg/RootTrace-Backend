from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HypothesisCreate(BaseModel):
    incident_id: UUID
    service_id: UUID | None = None
    title: str
    description: str | None = None
    score: int = Field(ge=0, le=100)
    status: str = "needs_investigation"


class HypothesisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    incident_id: UUID
    service_id: UUID | None
    title: str
    description: str | None
    score: int
    status: str
