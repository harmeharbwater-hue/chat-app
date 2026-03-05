from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class ContactRead(BaseModel):
    id: int
    user_id: int
    contact_user_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class ContactCreate(BaseModel):
    target_user_id: int


class ContactUpdate(BaseModel):
    action: Literal["accept", "block", "remove"]

