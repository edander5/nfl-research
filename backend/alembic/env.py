from alembic import context

from app.core.config import Settings
from app.db.base import Base
from app.db.session import make_engine
from app import models  # noqa: F401 -- register mappings for autogeneration


target_metadata = Base.metadata

if context.is_offline_mode():
    # No credentials are required to review PostgreSQL DDL offline.
    context.configure(
        dialect_name="postgresql", target_metadata=target_metadata,
        literal_binds=True, dialect_opts={"paramstyle": "named"}, compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()
else:
    # Tests can supply an isolated connection without touching development data.
    supplied_connection = context.config.attributes.get("connection")
    if supplied_connection is not None:
        context.configure(connection=supplied_connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
    else:
        engine = make_engine(Settings())
        try:
            with engine.connect() as connection:
                context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
                with context.begin_transaction():
                    context.run_migrations()
        finally:
            engine.dispose()
