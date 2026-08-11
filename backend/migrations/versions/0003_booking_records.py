"""Durable booking, payment, audit, and notification records."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_booking_records"
down_revision = "0002_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    booking_status = postgresql.ENUM(
        "PENDING",
        "CONFIRMED",
        "CANCELLED",
        "EXPIRED",
        name="booking_status",
        create_type=False,
    )
    seat_status = postgresql.ENUM(
        "CONFIRMED", "CANCELLED", name="booking_seat_status", create_type=False
    )
    payment_outcome = postgresql.ENUM(
        "SUCCESS", "FAILURE", "TIMEOUT", name="payment_outcome", create_type=False
    )
    payment_status = postgresql.ENUM(
        "SUCCEEDED", "FAILED", "TIMED_OUT", name="payment_status", create_type=False
    )
    notification_status = postgresql.ENUM(
        "PENDING", "SENT", "FAILED", name="notification_status", create_type=False
    )
    for enum_type in [
        booking_status,
        seat_status,
        payment_outcome,
        payment_status,
        notification_status,
    ]:
        enum_type.create(op.get_bind())
    op.create_table(
        "bookings",
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("organizer_id", sa.Uuid(), nullable=False),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.Column("status", booking_status, nullable=False),
        sa.Column("total_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("hold_id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("cancelled_at", sa.DateTime(timezone=True)),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["organizer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_bookings"),
    )
    op.create_index("ix_bookings_customer_status", "bookings", ["customer_id", "status"])
    op.create_index("ix_bookings_show_status", "bookings", ["show_id", "status"])
    op.create_index("ix_bookings_organizer_status", "bookings", ["organizer_id", "status"])
    op.create_table(
        "booking_seats",
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("show_id", sa.Uuid(), nullable=False),
        sa.Column("seat_id", sa.Uuid(), nullable=False),
        sa.Column(
            "category", postgresql.ENUM(name="seat_category", create_type=False), nullable=False
        ),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("status", seat_status, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.ForeignKeyConstraint(["show_id"], ["shows.id"]),
        sa.ForeignKeyConstraint(["seat_id"], ["seats.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_booking_seats"),
    )
    op.create_index(
        "uq_booking_seat_confirmed",
        "booking_seats",
        ["show_id", "seat_id"],
        unique=True,
        postgresql_where=sa.text("status = 'CONFIRMED'"),
    )
    op.create_table(
        "idempotency_records",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(120), nullable=False),
        sa.Column("endpoint", sa.String(120), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_idempotency_records"),
    )
    op.create_index(
        "uq_idempotency_user_key", "idempotency_records", ["user_id", "key"], unique=True
    )
    op.create_index("ix_idempotency_created", "idempotency_records", ["created_at"])
    op.create_table(
        "payment_attempts",
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("requested_outcome", payment_outcome, nullable=False),
        sa.Column("status", payment_status, nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_payment_attempts"),
    )
    op.create_index("ix_payment_booking_created", "payment_attempts", ["booking_id", "created_at"])
    op.create_table(
        "refunds",
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_refunds"),
    )
    op.create_index("ix_refunds_booking_created", "refunds", ["booking_id", "created_at"])
    op.create_table(
        "audit_events",
        sa.Column("actor_id", sa.Uuid()),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("entity_type", sa.String(80), nullable=False),
        sa.Column("entity_id", sa.String(64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
    )
    op.create_index("ix_audit_entity", "audit_events", ["entity_type", "entity_id"])
    op.create_index("ix_audit_created", "audit_events", ["created_at"])
    op.create_table(
        "notifications",
        sa.Column("booking_id", sa.Uuid(), nullable=False),
        sa.Column("recipient", sa.String(320), nullable=False),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("deduplication_key", sa.String(180), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["booking_id"], ["bookings.id"]),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
    )
    op.create_index(
        "uq_notification_deduplication", "notifications", ["deduplication_key"], unique=True
    )
    op.create_index("ix_notification_status_created", "notifications", ["status", "created_at"])


def downgrade() -> None:
    for table in [
        "notifications",
        "audit_events",
        "refunds",
        "payment_attempts",
        "idempotency_records",
        "booking_seats",
        "bookings",
    ]:
        op.drop_table(table)
    for name in [
        "notification_status",
        "payment_status",
        "payment_outcome",
        "booking_seat_status",
        "booking_status",
    ]:
        sa.Enum(name=name).drop(op.get_bind())
