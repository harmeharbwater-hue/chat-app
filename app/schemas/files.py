from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class FileAttachmentRead(BaseModel):
    id: int
    message_id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime

    class Config:
        from_attributes = True

