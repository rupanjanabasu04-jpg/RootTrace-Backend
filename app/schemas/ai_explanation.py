from typing import Any

from pydantic import BaseModel, ConfigDict


class AIExplanation(BaseModel):
    """Human-readable explanation of a deterministic incident analysis."""

    model_config = ConfigDict(extra="forbid")

    what_happened: list[str]
    probable_cause: str
    why_it_was_ranked: list[str]
    evidence: list[str]
    possible_propagation: list[str]
    what_to_investigate_next: list[str]
    uncertainty_and_limitations: list[str]


class IncidentExplanationResponse(BaseModel):
    """Deterministic analysis plus its separately generated AI explanation."""

    analysis: dict[str, Any]
    explanation: AIExplanation
