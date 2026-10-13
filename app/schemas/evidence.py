from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EvidenceCreate(BaseModel):
    hypothesis_id: UUID
    evidence_type: str
    source_id: UUID | None = None
    description: str
    strength: int = Field(ge=0, le=100)


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hypothesis_id: UUID
    evidence_type: str
    source_id: UUID | None
    description: str
    strength: int
