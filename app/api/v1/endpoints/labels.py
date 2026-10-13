from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.api.v1.dependencies import get_current_user
from app.api.v1.rbac import ProjectRole, require_project_role
from app.db.session import get_db
from app.models.label import Label, task_labels
from app.models.task import Task
from app.models.user import User
from app.schemas.label import LabelCreate, LabelResponse, LabelUpdate


router = APIRouter(
    prefix="/projects/{project_id}/labels",
    tags=["Labels"],
)


@router.get("", response_model=list[LabelResponse])
def list_labels(
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
        select(Label)
        .where(Label.project_id == project_id)
        .order_by(Label.name)
    ).all()


@router.post("", response_model=LabelResponse, status_code=201)
def create_label(
    project_id: UUID,
    payload: LabelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(
        project_id,
        ProjectRole.ADMIN,
        db,
        current_user,
    )

    existing = db.scalar(
        select(Label).where(
            Label.project_id == project_id,
            Label.name == payload.name.strip(),
        )
    )

    if existing:
        raise HTTPException(409, "Label already exists")

    label = Label(
        project_id=project_id,
        name=payload.name.strip(),
    )

    db.add(label)
    db.commit()
    db.refresh(label)

    return label


@router.patch(
    "/{label_id}",
    response_model=LabelResponse,
)
def update_label(
    project_id: UUID,
    label_id: UUID,
    payload: LabelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(
        project_id,
        ProjectRole.ADMIN,
        db,
        current_user,
    )

    label = db.scalar(
        select(Label).where(
            Label.id == label_id,
            Label.project_id == project_id,
        )
    )

    if label is None:
        raise HTTPException(404, "Label not found")

    label.name = payload.name.strip()

    db.commit()
    db.refresh(label)

    return label


@router.delete("/{label_id}", status_code=204)
def delete_label(
    project_id: UUID,
    label_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(
        project_id,
        ProjectRole.ADMIN,
        db,
        current_user,
    )

    label = db.scalar(
        select(Label).where(
            Label.id == label_id,
            Label.project_id == project_id,
        )
    )

    if label is None:
        raise HTTPException(404, "Label not found")

    db.delete(label)
    db.commit()

    return None


@router.post(
    "/{label_id}/tasks/{task_id}",
    status_code=204,
)
def attach_label(
    project_id: UUID,
    label_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(
        project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )

    label = db.scalar(
        select(Label).where(
            Label.id == label_id,
            Label.project_id == project_id,
        )
    )

    task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.project_id == project_id,
        )
    )

    if label is None or task is None:
        raise HTTPException(404, "Label or task not found")

    existing = db.execute(
        select(task_labels).where(
            task_labels.c.task_id == task_id,
            task_labels.c.label_id == label_id,
        )
    ).first()

    if not existing:
        db.execute(
            task_labels.insert().values(
                task_id=task_id,
                label_id=label_id,
            )
        )
        db.commit()

    return None


@router.delete(
    "/{label_id}/tasks/{task_id}",
    status_code=204,
)
def detach_label(
    project_id: UUID,
    label_id: UUID,
    task_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_project_role(
        project_id,
        ProjectRole.MEMBER,
        db,
        current_user,
    )

    label = db.scalar(
        select(Label).where(
            Label.id == label_id,
            Label.project_id == project_id,
        )
    )

    task = db.scalar(
        select(Task).where(
            Task.id == task_id,
            Task.project_id == project_id,
        )
    )

    if label is None or task is None:
        raise HTTPException(404, "Label or task not found")

    db.execute(
        delete(task_labels).where(
            task_labels.c.task_id == task_id,
            task_labels.c.label_id == label_id,
        )
    )

    db.commit()

    return None
