"""Venues, seats, events, shows, and prices."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_catalog"
down_revision = "0001_auth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    seat_category = postgresql.ENUM(
        "STANDARD", "PREMIUM", "VIP", name="seat_category", create_type=False
    )
    show_status = postgresql.ENUM("SCHEDULED", "CANCELLED", name="show_status", create_type=False)
    seat_category.create(op.get_bind())
    show_status.create(op.get_bind())
    op.create_table(
        "venues",
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("city", sa.String(120), nullable=False),
        sa.Column("address", sa.String(300), nullable=False),
        sa.Column("timezone", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_venues"),
    )
    op.create_index("ix_venues_city", "venues", ["city"])
    op.create_table(
        "venue_sections",
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_venue_sections"),
        sa.UniqueConstraint("venue_id", "name", name="uq_venue_section_name"),
    )
    op.create_table(
        "seats",
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("section_id", sa.Uuid(), nullable=False),
        sa.Column("row_label", sa.String(16), nullable=False),
        sa.Column("number", sa.Integer(), nullable=False),
        sa.Column("identifier", sa.String(120), nullable=False),
        sa.Column("category", seat_category, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["section_id"], ["venue_sections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_seats"),
        sa.UniqueConstraint("venue_id", "identifier", name="uq_seat_venue_identifier"),
    )
    op.create_index("ix_seats_venue_category", "seats", ["venue_id", "category"])
    op.create_table(
        "events",
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(80), nullable=False),
        sa.Column("image_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_events"),
    )
    op.create_index("ix_events_category", "events", ["category"])
    op.create_table(
        "shows",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("venue_id", sa.Uuid(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", show_status, nullable=False),
        sa.Column("currency", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.CheckConstraint("ends_at > starts_at", name="ck_shows_valid_time_range"),
        sa.ForeignKeyConstraint(["event_id"], ["events.id"]),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_shows"),
    )
    op.create_index("ix_shows_start_status", "shows", ["starts_at", "status"])
    op.create_index("ix_shows_venue_time", "shows", ["venue_id", "starts_at", "ends_at"])
    op.create_table(
        "show_prices",
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.Column("category", seat_category, nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name="pk_show_prices"),
        sa.UniqueConstraint("show_id", "category", name="uq_show_price_category"),
    )


def downgrade() -> None:
    for table in ["show_prices", "shows", "events", "seats", "venue_sections", "venues"]:
        op.drop_table(table)
    sa.Enum(name="show_status").drop(op.get_bind())
    sa.Enum(name="seat_category").drop(op.get_bind())
