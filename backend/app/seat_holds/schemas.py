from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HoldCreate(BaseModel):
    show_id: UUID
    seat_ids: list[UUID] = Field(min_length=1, max_length=5)

    @field_validator("seat_ids")
    @classmethod
    def unique_seats(cls, seat_ids: list[UUID]) -> list[UUID]:
        if len(seat_ids) != len(set(seat_ids)):
            raise ValueError("Seat IDs must be unique")
        return seat_ids


class HoldRead(BaseModel):
    hold_id: UUID
    show_id: UUID
    seat_ids: list[UUID]
    expires_at: datetime
