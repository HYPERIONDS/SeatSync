from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.audit import models as audit_models  # noqa: F401
from app.bookings import models as booking_models  # noqa: F401
from app.core.config import get_settings
from app.database.base import Base
from app.events import models as event_models  # noqa: F401
from app.notifications import models as notification_models  # noqa: F401
from app.payments import models as payment_models  # noqa: F401
from app.reporting import models as reporting_models  # noqa: F401
from app.shows import models as show_models  # noqa: F401
from app.users import models as user_models  # noqa: F401
from app.venues import models as venue_models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
