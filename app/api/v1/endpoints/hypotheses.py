from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.hypothesis import Hypothesis
from app.schemas.hypothesis import HypothesisCreate, HypothesisResponse


router = APIRouter(
    prefix="/hypotheses",
    tags=["Hypotheses"],
)


@router.post(
    "",
    response_model=HypothesisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_hypothesis(
    hypothesis_data: HypothesisCreate,
    db: Session = Depends(get_db),
):
    hypothesis = Hypothesis(
        incident_id=hypothesis_data.incident_id,
        service_id=hypothesis_data.service_id,
        title=hypothesis_data.title,
        description=hypothesis_data.description,
        score=hypothesis_data.score,
        status=hypothesis_data.status,
    )

    db.add(hypothesis)
    db.commit()
    db.refresh(hypothesis)

    return hypothesis


@router.get(
    "",
    response_model=list[HypothesisResponse],
)
def list_hypotheses(
    db: Session = Depends(get_db),
):
    hypotheses = (
        db.query(Hypothesis)
        .order_by(Hypothesis.score.desc())
        .all()
    )

    return hypotheses
