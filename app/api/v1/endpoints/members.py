from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import (
    ProjectRole,
    require_project_admin_or_higher,
    require_project_viewer_or_higher,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.schemas.project_member import (
    ProjectMemberCreate,
    ProjectMemberDetailResponse,
    ProjectMemberRoleUpdate,
)
from app.services.activity_service import record_activity, create_notification


router = APIRouter(
    prefix="/projects/{project_id}/members",
    tags=["Project Members"],
)


def get_project_or_404(
    project_id: UUID,
    db: Session,
) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


@router.get(
    "",
    response_model=list[ProjectMemberDetailResponse],
)
def list_members(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_viewer_or_higher(
        project_id,
        db,
        current_user,
    )

    get_project_or_404(project_id, db)

    rows = db.execute(
        select(ProjectMember, User)
        .join(User, User.id == ProjectMember.user_id)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    ).all()

    result = []

    for membership, user in rows:
        result.append(
            ProjectMemberDetailResponse(
                id=membership.id,
                project_id=membership.project_id,
                user_id=membership.user_id,
                role=membership.role,
                created_at=membership.created_at,
                updated_at=membership.updated_at,
                email=user.email,
                full_name=user.full_name,
            )
        )

    return result


@router.post(
    "",
    response_model=ProjectMemberDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_member(
    project_id: UUID,
    payload: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_admin_or_higher(
        project_id,
        db,
        current_user,
    )

    project = get_project_or_404(project_id, db)

    user = db.scalar(
        select(User).where(User.email == payload.email)
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is inactive",
        )

    if user.id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project owner does not need a membership",
        )

    existing = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )

    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a project member",
        )

    membership = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=payload.role,
    )

    db.add(membership)
    db.flush()

    record_activity(
        db,
        project_id=project_id,
        user_id=current_user.id,
        action="member_added",
        entity_type="project_member",
        entity_id=membership.id,
        description=f"{user.full_name} was added to the project as {membership.role}",
    )

    if user.id != current_user.id:
        create_notification(
            db,
            user_id=user.id,
            project_id=project_id,
            notification_type="project_membership",
            title="Added to project",
            message=f"You were added to '{project.name}' as a {membership.role}",
        )

    db.commit()
    db.refresh(membership)

    return ProjectMemberDetailResponse(
        id=membership.id,
        project_id=membership.project_id,
        user_id=membership.user_id,
        role=membership.role,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        email=user.email,
        full_name=user.full_name,
    )


@router.patch(
    "/{user_id}",
    response_model=ProjectMemberDetailResponse,
)
def update_member_role(
    project_id: UUID,
    user_id: UUID,
    payload: ProjectMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_admin_or_higher(
        project_id,
        db,
        current_user,
    )

    project = get_project_or_404(project_id, db)

    if user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project owner role cannot be changed",
        )

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    old_role = membership.role
    membership.role = payload.role

    record_activity(
        db,
        project_id=project_id,
        user_id=current_user.id,
        action="member_role_changed",
        entity_type="project_member",
        entity_id=membership.id,
        description=f"Project member role changed from {old_role} to {membership.role}",
    )

    if user_id != current_user.id:
        create_notification(
            db,
            user_id=user_id,
            project_id=project_id,
            notification_type="role_changed",
            title="Project role changed",
            message=f"Your role in '{project.name}' changed from {old_role} to {membership.role}",
        )

    db.commit()
    db.refresh(membership)

    user = db.scalar(
        select(User).where(User.id == user_id)
    )

    return ProjectMemberDetailResponse(
        id=membership.id,
        project_id=membership.project_id,
        user_id=membership.user_id,
        role=membership.role,
        created_at=membership.created_at,
        updated_at=membership.updated_at,
        email=user.email,
        full_name=user.full_name,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_member(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_admin_or_higher(
        project_id,
        db,
        current_user,
    )

    project = get_project_or_404(project_id, db)

    if user_id == project.owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project owner cannot be removed",
        )

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project member not found",
        )

    record_activity(
        db,
        project_id=project_id,
        user_id=current_user.id,
        action="member_removed",
        entity_type="project_member",
        entity_id=membership.id,
        description=f"Project member {user_id} was removed",
    )

    if user_id != current_user.id:
        create_notification(
            db,
            user_id=user_id,
            project_id=project_id,
            notification_type="removed_from_project",
            title="Removed from project",
            message=f"You were removed from project '{project.name}'",
        )

    db.delete(membership)
    db.commit()

    return None
