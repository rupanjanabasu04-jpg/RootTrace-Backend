from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import ProjectRole, require_project_role
from app.db.session import get_db
from app.models.activity import Activity
from app.models.user import User
from app.schemas.activity import ActivityResponse


router = APIRouter(
    prefix="/projects/{project_id}/activity",
    tags=["Activity"],
)


@router.get(
    "",
    response_model=list[ActivityResponse],
)
def list_activity(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(
        project_id,
        ProjectRole.VIEWER,
        db,
        current_user,
    )

    return db.scalars(
        select(Activity)
        .where(Activity.project_id == project_id)
        .order_by(Activity.created_at.desc())
    ).all()
