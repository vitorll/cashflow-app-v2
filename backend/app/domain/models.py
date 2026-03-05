import uuid

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func, text

from app.domain.enums import ImportStatus, VersionType, SourceType


class Base(DeclarativeBase):
    pass


class Import(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(sa.String, nullable=False)
    status: Mapped[ImportStatus] = mapped_column(
        sa.Enum(ImportStatus, name="import_status_enum", create_type=False),
        nullable=False,
        default=ImportStatus.pending,
    )
    version_type: Mapped[VersionType] = mapped_column(
        sa.Enum(VersionType, name="version_type_enum", create_type=False),
        nullable=False,
    )
    source_type: Mapped[SourceType] = mapped_column(
        sa.Enum(SourceType, name="source_type_enum", create_type=False),
        nullable=False,
    )
    created_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[sa.DateTime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    deleted_at: Mapped[sa.DateTime | None] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
    )
