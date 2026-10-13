from enum import Enum
from uuid import UUID

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User


class ProjectRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


ROLE_LEVEL = {
    ProjectRole.VIEWER: 1,
    ProjectRole.MEMBER: 2,
    ProjectRole.ADMIN: 3,
    ProjectRole.OWNER: 4,
}


def get_project_role(
    project_id: UUID,
    current_user: User,
    db: Session,
) -> ProjectRole | None:

    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        return None

    if project.owner_id == current_user.id:
        return ProjectRole.OWNER

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        )
    )

    if membership is None:
        return None

    try:
        return ProjectRole(membership.role)
    except ValueError:
        return None


def require_project_role(
    project_id: UUID,
    minimum_role: ProjectRole,
    db: Session,
    current_user: User,
) -> ProjectRole:

    role = get_project_role(
        project_id,
        current_user,
        db,
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )

    if ROLE_LEVEL[role] < ROLE_LEVEL[minimum_role]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{minimum_role.value} role or higher is required",
        )

    return role


def require_project_viewer_or_higher(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_project_role(
        project_id,
        ProjectRole.VIEWER,
        db,
        current_user,
    )


def require_project_member_or_higher(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_project_role(
        project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )


def require_project_admin_or_higher(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_project_role(
        project_id,
        ProjectRole.ADMIN,
        db,
        current_user,
    )


def require_project_owner(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return require_project_role(
        project_id,
        ProjectRole.OWNER,
        db,
        current_user,
    )
