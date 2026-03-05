import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.enums import ImportStatus, VersionType, SourceType


class ImportBase(BaseModel):
    name: str
    version_type: VersionType
    source_type: SourceType


class ImportCreate(ImportBase):
    pass


class ImportResponse(ImportBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: ImportStatus
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
