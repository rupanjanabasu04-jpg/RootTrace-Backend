from uuid import UUID

from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.notification import Notification


def record_activity(
    db: Session,
    *,
    project_id: UUID,
    user_id: UUID | None,
    action: str,
    entity_type: str,
    entity_id: UUID | None = None,
    description: str,
) -> Activity:
    activity = Activity(
        project_id=project_id,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        description=description,
    )

    db.add(activity)
    return activity


def create_notification(
    db: Session,
    *,
    user_id: UUID,
    title: str,
    message: str,
    notification_type: str,
    project_id: UUID | None = None,
    task_id: UUID | None = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        project_id=project_id,
        task_id=task_id,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False,
    )

    db.add(notification)
    return notification


def notify_users(
    db: Session,
    *,
    user_ids: set[UUID],
    exclude_user_id: UUID | None = None,
    title: str,
    message: str,
    notification_type: str,
    project_id: UUID | None = None,
    task_id: UUID | None = None,
) -> None:
    for user_id in user_ids:
        if exclude_user_id is not None and user_id == exclude_user_id:
            continue

        create_notification(
            db,
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            project_id=project_id,
            task_id=task_id,
        )
