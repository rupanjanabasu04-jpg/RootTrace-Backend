from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.deployment import Deployment
from app.schemas.deployment import DeploymentCreate, DeploymentResponse


router = APIRouter(
    prefix="/deployments",
    tags=["Deployments"],
)


@router.post(
    "",
    response_model=DeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_deployment(
    deployment_data: DeploymentCreate,
    db: Session = Depends(get_db),
):
    deployment = Deployment(
        incident_id=deployment_data.incident_id,
        service_id=deployment_data.service_id,
        change_type=deployment_data.change_type,
        version=deployment_data.version,
        description=deployment_data.description,
        occurred_at=deployment_data.occurred_at,
    )

    db.add(deployment)
    db.commit()
    db.refresh(deployment)

    return deployment


@router.get(
    "",
    response_model=list[DeploymentResponse],
)
def list_deployments(
    db: Session = Depends(get_db),
):
    deployments = (
        db.query(Deployment)
        .order_by(Deployment.occurred_at.asc())
        .all()
    )

    return deployments
