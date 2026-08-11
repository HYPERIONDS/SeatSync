from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.shows.models import ShowStatus
from app.venues.models import SeatCategory


class PriceCreate(BaseModel):
    category: SeatCategory
    amount_minor: int = Field(gt=0, le=100_000_000)


class ShowCreate(BaseModel):
    venue_id: UUID
    starts_at: datetime
    ends_at: datetime
    currency: str = Field(default="INR", min_length=3, max_length=3)
    prices: list[PriceCreate] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def validate_show(self):
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be after starts_at")
        categories = [price.category for price in self.prices]
        if len(categories) != len(set(categories)):
            raise ValueError("Price categories must be unique")
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("Show timestamps must include a timezone")
        return self


class PriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category: SeatCategory
    amount_minor: int


class ShowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    event_id: UUID
    venue_id: UUID
    starts_at: datetime
    ends_at: datetime
    status: ShowStatus
    currency: str
    prices: list[PriceRead]
