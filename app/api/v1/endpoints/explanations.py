from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.ai_explanation import IncidentExplanationResponse
from app.services.ai_explanation import (
    AIExplanationConfigurationError,
    AIExplanationError,
    generate_ai_explanation,
)
from app.services.incident_analyzer import analyze_incident


router = APIRouter(
    prefix="/incidents",
    tags=["AI Explanations"],
)


@router.get(
    "/{incident_id}/explanation",
    response_model=IncidentExplanationResponse,
)
def get_incident_explanation(
    incident_id: UUID,
    db: Session = Depends(get_db),
):
    """Return an unchanged deterministic analysis and its AI explanation."""

    analysis = analyze_incident(incident_id=incident_id, db=db)

    try:
        explanation = generate_ai_explanation(analysis)
    except AIExplanationConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except AIExplanationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI explanation generation failed.",
        ) from exc

    return {
        "analysis": analysis,
        "explanation": explanation,
    }
