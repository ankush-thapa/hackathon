from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app import models  # Register all models in Base.metadata.
from app.core.config import settings
from app.db.session import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online():
    engine = create_engine(settings.DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    raise RuntimeError(
        "This migration inspects the existing schema. Run alembic upgrade head "
        "without --sql, using DATABASE_URL or the project's .env file."
    )
else:
    run_migrations_online()
