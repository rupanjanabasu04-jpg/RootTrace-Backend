from pathlib import Path
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import ProjectRole, require_project_role
from app.db.session import get_db
from app.models.attachment import Attachment
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.schemas.attachment import AttachmentResponse


router = APIRouter(tags=["Attachments"])

UPLOAD_DIR = Path("outputs/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 10 * 1024 * 1024


def get_task(task_id, db):
    task = db.scalar(
        select(Task).where(Task.id == task_id)
    )

    if task is None:
        raise HTTPException(404, "Task not found")

    return task


@router.post(
    "/tasks/{task_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
)
async def upload_attachment(
    task_id: UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(task_id, db)

    require_project_role(
        task.project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )

    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            "File is too large. Maximum size is 10 MB",
        )

    if not file.filename:
        raise HTTPException(
            400,
            "Filename is required",
        )

    stored_name = f"{uuid4()}_{Path(file.filename).name}"
    destination = UPLOAD_DIR / stored_name

    destination.write_bytes(content)

    attachment = Attachment(
        task_id=task.id,
        uploaded_by=current_user.id,
        original_filename=Path(file.filename).name,
        stored_filename=stored_name,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(content),
        file_path=str(destination),
    )

    db.add(attachment)
    db.commit()
    db.refresh(attachment)

    return attachment


@router.get(
    "/tasks/{task_id}/attachments",
    response_model=list[AttachmentResponse],
)
def list_attachments(
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = get_task(task_id, db)

    require_project_role(
        task.project_id,
        ProjectRole.VIEWER,
        db,
        current_user,
    )

    return db.scalars(
        select(Attachment)
        .where(Attachment.task_id == task_id)
        .order_by(Attachment.created_at.desc())
    ).all()


@router.delete(
    "/attachments/{attachment_id}",
    status_code=204,
)
def delete_attachment(
    attachment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attachment = db.scalar(
        select(Attachment).where(
            Attachment.id == attachment_id
        )
    )

    if attachment is None:
        raise HTTPException(404, "Attachment not found")

    task = get_task(attachment.task_id, db)

    role = require_project_role(
        task.project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )

    if (
        attachment.uploaded_by != current_user.id
        and role not in (ProjectRole.ADMIN, ProjectRole.OWNER)
    ):
        raise HTTPException(
            403,
            "You cannot delete this attachment",
        )

    path = Path(attachment.file_path)

    if path.exists():
        path.unlink()

    db.delete(attachment)
    db.commit()

    return None
