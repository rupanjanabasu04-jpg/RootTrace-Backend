from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import ProjectRole, require_project_role
from app.db.session import get_db
from app.models.comment import Comment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse, CommentUpdate
from app.services.activity_service import record_activity, notify_users


router = APIRouter(tags=["Comments"])


def get_task_access(task_id, db, user):
    task = db.scalar(
        select(Task)
        .join(Project, Project.id == Task.project_id)
        .where(Task.id == task_id)
    )

    if task is None:
        raise HTTPException(404, "Task not found")

    require_project_role(
        task.project_id,
        ProjectRole.MEMBER,
        db,
        user,
    )

    return task


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=201,
)
def create_comment(
    task_id: UUID,
    payload: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task_access(task_id, db, current_user)

    comment = Comment(
        task_id=task.id,
        user_id=current_user.id,
        content=payload.content.strip(),
    )

    db.add(comment)
    db.flush()

    record_activity(
        db,
        project_id=task.project_id,
        user_id=current_user.id,
        action="created",
        entity_type="comment",
        entity_id=comment.id,
        description=f"Comment added to task '{task.title}'",
    )

    recipient_ids = set()

    if task.assignee_id is not None:
        recipient_ids.add(task.assignee_id)

    project = db.scalar(
        select(Project).where(Project.id == task.project_id)
    )

    if project is not None:
        recipient_ids.add(project.owner_id)

    notify_users(
        db,
        user_ids=recipient_ids,
        exclude_user_id=current_user.id,
        project_id=task.project_id,
        task_id=task.id,
        notification_type="comment_added",
        title="New comment",
        message=f"{current_user.full_name} commented on task '{task.title}'",
    )

    db.commit()
    db.refresh(comment)

    return comment


@router.get(
    "/tasks/{task_id}/comments",
    response_model=list[CommentResponse],
)
def list_comments(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = db.scalar(
        select(Task).where(Task.id == task_id)
    )

    if task is None:
        raise HTTPException(404, "Task not found")

    require_project_role(
        task.project_id,
        ProjectRole.VIEWER,
        db,
        current_user,
    )

    return db.scalars(
        select(Comment)
        .where(Comment.task_id == task_id)
        .order_by(Comment.created_at.asc())
    ).all()


@router.patch(
    "/comments/{comment_id}",
    response_model=CommentResponse,
)
def update_comment(
    comment_id: UUID,
    payload: CommentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.scalar(
        select(Comment).where(Comment.id == comment_id)
    )

    if comment is None:
        raise HTTPException(404, "Comment not found")

    task = db.scalar(
        select(Task).where(Task.id == comment.task_id)
    )

    require_project_role(
        task.project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )

    if comment.user_id != current_user.id:
        raise HTTPException(
            403,
            "You can only edit your own comments",
        )

    comment.content = payload.content.strip()

    db.commit()
    db.refresh(comment)

    return comment


@router.delete(
    "/comments/{comment_id}",
    status_code=204,
)
def delete_comment(
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    comment = db.scalar(
        select(Comment).where(Comment.id == comment_id)
    )

    if comment is None:
        raise HTTPException(404, "Comment not found")

    task = db.scalar(
        select(Task).where(Task.id == comment.task_id)
    )

    role = require_project_role(
        task.project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )

    if comment.user_id != current_user.id and role not in (
        ProjectRole.ADMIN,
        ProjectRole.OWNER,
    ):
        raise HTTPException(
            403,
            "You can only delete your own comments",
        )

    record_activity(
        db,
        project_id=task.project_id,
        user_id=current_user.id,
        action="deleted",
        entity_type="comment",
        entity_id=comment.id,
        description=f"Comment deleted from task '{task.title}'",
    )

    db.delete(comment)
    db.commit()

    return None
