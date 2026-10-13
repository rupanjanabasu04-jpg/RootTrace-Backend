from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import (
    ProjectRole,
    get_project_role,
    require_project_admin_or_higher,
    require_project_member_or_higher,
    require_project_owner,
    require_project_viewer_or_higher,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.activity_service import record_activity


router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = Project(
        name=payload.name.strip(),
        description=payload.description,
        owner_id=current_user.id,
    )

    db.add(project)
    db.flush()

    record_activity(
        db,
        project_id=project.id,
        user_id=current_user.id,
        action="created",
        entity_type="project",
        entity_id=project.id,
        description=f"Project '{project.name}' was created",
    )

    db.commit()
    db.refresh(project)

    return project


@router.get(
    "",
    response_model=list[ProjectResponse],
)
def list_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    owned_projects = db.scalars(
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
    ).all()

    member_projects = db.scalars(
        select(Project)
        .join(
            ProjectMember,
            ProjectMember.project_id == Project.id,
        )
        .where(ProjectMember.user_id == current_user.id)
        .order_by(Project.created_at.desc())
    ).all()

    seen = set()
    projects = []

    for project in [*owned_projects, *member_projects]:
        if project.id not in seen:
            seen.add(project.id)
            projects.append(project)

    return projects


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_viewer_or_higher(
        project_id,
        db,
        current_user,
    )

    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
)
def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_owner(
        project_id,
        db,
        current_user,
    )

    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if payload.name is not None:
        cleaned_name = payload.name.strip()

        if not cleaned_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project name cannot be empty",
            )

        project.name = cleaned_name

    if payload.description is not None:
        project.description = payload.description

    db.commit()
    db.refresh(project)

    return project


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_owner(
        project_id,
        db,
        current_user,
    )

    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    db.delete(project)
    db.commit()

    return None
