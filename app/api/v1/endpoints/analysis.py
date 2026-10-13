from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.incident_analyzer import analyze_incident


router = APIRouter(
    prefix="/incidents",
    tags=["Analysis"],
)


@router.get("/{incident_id}/analysis")
def get_incident_analysis(
    incident_id: UUID,
    db: Session = Depends(get_db),
):
    return analyze_incident(
        incident_id=incident_id,
        db=db,
    )
