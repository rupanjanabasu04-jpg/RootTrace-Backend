from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.event import Event
from app.schemas.event import EventCreate, EventResponse


router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_event(
    event_data: EventCreate,
    db: Session = Depends(get_db),
):
    event = Event(
        incident_id=event_data.incident_id,
        service_id=event_data.service_id,
        event_type=event_data.event_type,
        message=event_data.message,
        occurred_at=event_data.occurred_at,
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return event


@router.get(
    "",
    response_model=list[EventResponse],
)
def list_events(
    db: Session = Depends(get_db),
):
    events = (
        db.query(Event)
        .order_by(Event.occurred_at.asc())
        .all()
    )

    return events
