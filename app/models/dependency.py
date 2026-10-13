from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ServiceDependency(Base):
    __tablename__ = "service_dependencies"

    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    source_service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=False,
    )

    target_service_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("services.id"),
        nullable=False,
    )

    dependency_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="runtime",
    )

