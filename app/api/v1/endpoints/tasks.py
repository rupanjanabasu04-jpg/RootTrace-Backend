from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import (
    ProjectRole,
    get_project_role,
    require_project_member_or_higher,
    require_project_viewer_or_higher,
)
from app.db.session import get_db
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.activity_service import record_activity, create_notification


router = APIRouter(prefix="/tasks", tags=["Tasks"])


def get_task_or_404(
    task_id: UUID,
    db: Session,
) -> Task:
    task = db.scalar(
        select(Task).where(Task.id == task_id)
    )

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task


def validate_assignee(
    assignee_id: UUID | None,
    project_id: UUID,
    db: Session,
) -> None:
    if assignee_id is None:
        return

    assignee = db.scalar(
        select(User).where(User.id == assignee_id)
    )

    if assignee is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee user not found",
        )

    if not assignee.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee user is inactive",
        )

    # The assignee must actually belong to this project.
    # The project owner is automatically considered part of the project.
    project = db.scalar(
        select(Project).where(Project.id == project_id)
    )

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if assignee.id == project.owner_id:
        return

    from app.models.project_member import ProjectMember

    membership = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == assignee.id,
        )
    )

    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignee is not a member of this project",
        )


def validate_parent_task(
    parent_task_id: UUID | None,
    project_id: UUID,
    db: Session,
) -> None:
    if parent_task_id is None:
        return

    parent_task = db.scalar(
        select(Task).where(
            Task.id == parent_task_id,
            Task.project_id == project_id,
        )
    )

    if parent_task is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent task not found in this project",
        )


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_member_or_higher(
        payload.project_id,
        db,
        current_user,
    )

    validate_assignee(
        payload.assignee_id,
        payload.project_id,
        db,
    )

    validate_parent_task(
        payload.parent_task_id,
        payload.project_id,
        db,
    )

    task = Task(
        project_id=payload.project_id,
        title=payload.title.strip(),
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        created_by=current_user.id,
        assignee_id=payload.assignee_id,
        parent_task_id=payload.parent_task_id,
        due_date=payload.due_date,
    )

    db.add(task)
    db.flush()

    record_activity(
        db,
        project_id=task.project_id,
        user_id=current_user.id,
        action="created",
        entity_type="task",
        entity_id=task.id,
        description=f"Task '{task.title}' was created",
    )

    if task.assignee_id is not None and task.assignee_id != current_user.id:
        create_notification(
            db,
            user_id=task.assignee_id,
            project_id=task.project_id,
            task_id=task.id,
            notification_type="task_assigned",
            title="Task assigned to you",
            message=f"You were assigned task '{task.title}'",
        )

    db.commit()
    db.refresh(task)

    return task


@router.get(
    "",
    response_model=list[TaskResponse],
)
def list_tasks(
    project_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if project_id is not None:
        require_project_viewer_or_higher(
            project_id,
            db,
            current_user,
        )

        query = (
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at.desc())
        )

        return db.scalars(query).all()

    # No project_id supplied:
    # return tasks from projects the user owns or belongs to.
    from app.models.project_member import ProjectMember

    owned_project_ids = select(Project.id).where(
        Project.owner_id == current_user.id
    )

    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == current_user.id
    )

    query = (
        select(Task)
        .where(
            Task.project_id.in_(owned_project_ids.union(member_project_ids))
        )
        .order_by(Task.created_at.desc())
    )

    return db.scalars(query).all()


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
def get_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_or_404(task_id, db)

    require_project_viewer_or_higher(
        task.project_id,
        db,
        current_user,
    )

    return task


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    task_id: UUID,
    payload: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_or_404(task_id, db)

    role = require_project_member_or_higher(
        task.project_id,
        db,
        current_user,
    )

    old_status = task.status
    old_assignee_id = task.assignee_id
    old_title = task.title

    if payload.title is not None:
        cleaned_title = payload.title.strip()

        if not cleaned_title:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Task title cannot be empty",
            )

        task.title = cleaned_title

    if payload.description is not None:
        task.description = payload.description

    if payload.status is not None:
        task.status = payload.status

    if payload.priority is not None:
        task.priority = payload.priority

    if payload.assignee_id is not None:
        validate_assignee(
            payload.assignee_id,
            task.project_id,
            db,
        )
        task.assignee_id = payload.assignee_id

    if payload.parent_task_id is not None:
        if payload.parent_task_id == task.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A task cannot be its own parent",
            )

        validate_parent_task(
            payload.parent_task_id,
            task.project_id,
            db,
        )

        task.parent_task_id = payload.parent_task_id

    if payload.due_date is not None:
        task.due_date = payload.due_date

    record_activity(
        db,
        project_id=task.project_id,
        user_id=current_user.id,
        action="updated",
        entity_type="task",
        entity_id=task.id,
        description=f"Task '{old_title}' was updated",
    )

    if old_assignee_id != task.assignee_id and task.assignee_id is not None:
        if task.assignee_id != current_user.id:
            create_notification(
                db,
                user_id=task.assignee_id,
                project_id=task.project_id,
                task_id=task.id,
                notification_type="task_assigned",
                title="Task assigned to you",
                message=f"You were assigned task '{task.title}'",
            )

    if old_status != task.status:
        if (
            task.assignee_id is not None
            and task.assignee_id != current_user.id
        ):
            create_notification(
                db,
                user_id=task.assignee_id,
                project_id=task.project_id,
                task_id=task.id,
                notification_type="task_status_changed",
                title="Task status changed",
                message=f"Task '{task.title}' changed from '{old_status}' to '{task.status}'",
            )

    db.commit()
    db.refresh(task)

    return task


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_task(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_or_404(task_id, db)

    role = get_project_role(
        task.project_id,
        current_user,
        db,
    )

    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )

    # Only project admins and the owner can delete tasks.
    if role not in {
        ProjectRole.ADMIN,
        ProjectRole.OWNER,
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="admin role or higher is required to delete tasks",
        )

    task_title = task.title
    project_id = task.project_id
    task_id = task.id

    record_activity(
        db,
        project_id=project_id,
        user_id=current_user.id,
        action="deleted",
        entity_type="task",
        entity_id=task_id,
        description=f"Task '{task_title}' was deleted",
    )

    db.delete(task)
    db.commit()

    return None
