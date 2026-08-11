from datetime import UTC, datetime


def utcnow() -> datetime:
    return datetime.now(UTC)


def as_utc(value: datetime) -> datetime:
    """Normalize database timestamps; SQLite drops timezone metadata in tests."""
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
