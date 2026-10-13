from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


TaskStatus = Literal[
    "todo",
    "in_progress",
    "blocked",
    "done",
]

TaskPriority = Literal[
    "low",
    "medium",
    "high",
    "urgent",
]


class TaskCreate(BaseModel):
    project_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus = "todo"
    priority: TaskPriority = "medium"
    assignee_id: UUID | None = None
    parent_task_id: UUID | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=10000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    assignee_id: UUID | None = None
    parent_task_id: UUID | None = None
    due_date: datetime | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    title: str
    description: str | None
    status: str
    priority: str
    created_by: UUID
    assignee_id: UUID | None
    parent_task_id: UUID | None
    due_date: datetime | None
    created_at: datetime
    updated_at: datetime
