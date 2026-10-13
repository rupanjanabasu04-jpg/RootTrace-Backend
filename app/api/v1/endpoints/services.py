from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.service import Service
from app.schemas.service import ServiceCreate, ServiceResponse


router = APIRouter(prefix="/services", tags=["Services"])


@router.post(
    "",
    response_model=ServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_service(
    service_data: ServiceCreate,
    db: Session = Depends(get_db),
):
    service = Service(
        name=service_data.name,
        description=service_data.description,
    )

    db.add(service)
    db.commit()
    db.refresh(service)

    return service


@router.get(
    "",
    response_model=list[ServiceResponse],
)
def list_services(
    db: Session = Depends(get_db),
):
    services = (
        db.query(Service)
        .order_by(Service.name.asc())
        .all()
    )

    return services
