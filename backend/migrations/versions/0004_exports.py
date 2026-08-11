"""Organizer attendee export jobs."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0004_exports"
down_revision = "0003_booking_records"
branch_labels = None
depends_on = None


def upgrade() -> None:
    export_status = postgresql.ENUM(
        "PENDING", "COMPLETED", "FAILED", name="export_status", create_type=False
    )
    export_status.create(op.get_bind())
    op.create_table(
        "attendee_exports",
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.Column("status", export_status, nullable=False),
        sa.Column("file_path", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_attendee_exports"),
    )
    op.create_index(
        "ix_exports_organizer_created", "attendee_exports", ["organizer_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("attendee_exports")
    sa.Enum(name="export_status").drop(op.get_bind())
