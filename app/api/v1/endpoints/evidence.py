from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evidence import Evidence
from app.schemas.evidence import EvidenceCreate, EvidenceResponse


router = APIRouter(
    prefix="/evidence",
    tags=["Evidence"],
)


@router.post(
    "",
    response_model=EvidenceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_evidence(
    evidence_data: EvidenceCreate,
    db: Session = Depends(get_db),
):
    evidence = Evidence(
        hypothesis_id=evidence_data.hypothesis_id,
        evidence_type=evidence_data.evidence_type,
        source_id=evidence_data.source_id,
        description=evidence_data.description,
        strength=evidence_data.strength,
    )

    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    return evidence


@router.get(
    "",
    response_model=list[EvidenceResponse],
)
def list_evidence(
    db: Session = Depends(get_db),
):
    evidence = (
        db.query(Evidence)
        .order_by(Evidence.strength.desc())
        .all()
    )

    return evidence
