from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.dependency import ServiceDependency
from app.schemas.dependency import DependencyCreate, DependencyResponse


router = APIRouter(
    prefix="/dependencies",
    tags=["Dependencies"],
)


@router.post(
    "",
    response_model=DependencyResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_dependency(
    dependency_data: DependencyCreate,
    db: Session = Depends(get_db),
):
    dependency = ServiceDependency(
        source_service_id=dependency_data.source_service_id,
        target_service_id=dependency_data.target_service_id,
        dependency_type=dependency_data.dependency_type,
    )

    db.add(dependency)
    db.commit()
    db.refresh(dependency)

    return dependency


@router.get(
    "",
    response_model=list[DependencyResponse],
)
def list_dependencies(
    db: Session = Depends(get_db),
):
    dependencies = db.query(ServiceDependency).all()

    return dependencies
