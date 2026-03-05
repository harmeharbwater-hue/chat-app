from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MessageCreate(BaseModel):
    to_user_id: int
    body: str


class MessageRead(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    body: str
    meta: Optional[str] = None
    created_at: datetime
    deleted_at: Optional[datetime] = None

    class Config:
        from_attributes = True

