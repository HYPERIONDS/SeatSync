from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    description: str = Field(min_length=10, max_length=5000)
    category: str = Field(min_length=2, max_length=80)
    image_url: str | None = Field(default=None, max_length=500)


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organizer_id: UUID
    title: str
    description: str
    category: str
    image_url: str | None
    created_at: datetime
