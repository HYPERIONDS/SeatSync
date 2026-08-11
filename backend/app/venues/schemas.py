from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.venues.models import SeatCategory


class RowDefinition(BaseModel):
    label: str = Field(min_length=1, max_length=16)
    seat_count: int = Field(ge=1, le=200)
    category: SeatCategory = SeatCategory.STANDARD


class SectionDefinition(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    rows: list[RowDefinition] = Field(min_length=1, max_length=100)

    @field_validator("rows")
    @classmethod
    def unique_rows(cls, rows: list[RowDefinition]) -> list[RowDefinition]:
        labels = [row.label.upper() for row in rows]
        if len(labels) != len(set(labels)):
            raise ValueError("Row labels must be unique within a section")
        return rows


class VenueCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    city: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=3, max_length=300)
    timezone: str = Field(default="UTC", max_length=64)
    sections: list[SectionDefinition] = Field(min_length=1, max_length=30)

    @field_validator("sections")
    @classmethod
    def unique_sections(cls, sections: list[SectionDefinition]) -> list[SectionDefinition]:
        names = [section.name.casefold() for section in sections]
        if len(names) != len(set(names)):
            raise ValueError("Section names must be unique")
        return sections


class SeatRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    row_label: str
    number: int
    identifier: str
    category: SeatCategory


class SectionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    sort_order: int
    seats: list[SeatRead]


class VenueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    organizer_id: UUID
    name: str
    city: str
    address: str
    timezone: str
    sections: list[SectionRead]
