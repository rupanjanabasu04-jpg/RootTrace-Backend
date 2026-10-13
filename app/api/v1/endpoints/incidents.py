from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.incident import Incident
from app.schemas.incident import IncidentCreate, IncidentResponse


router = APIRouter(prefix="/incidents", tags=["Incidents"])


@router.post(
    "",
    response_model=IncidentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_incident(
    incident_data: IncidentCreate,
    db: Session = Depends(get_db),
):
    incident = Incident(
        title=incident_data.title,
        description=incident_data.description,
    )

    db.add(incident)
    db.commit()
    db.refresh(incident)

    return incident


@router.get(
    "",
    response_model=list[IncidentResponse],
)
def list_incidents(
    db: Session = Depends(get_db),
):
    incidents = (
        db.query(Incident)
        .order_by(Incident.created_at.desc())
        .all()
    )

    return incidents
