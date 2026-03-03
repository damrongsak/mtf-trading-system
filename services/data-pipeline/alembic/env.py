from logging.config import fileConfig
import os
import sys
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.database import Base, DATABASE_URL

# Import ALL system models to ensure they're registered with Base.metadata
# data-pipeline models
from app.models import candle, market, data_source, sentiment, economic_event, execution, cot, news, system_config, open_interest

# Add sibling services to path to import their models
# Note: In Docker, these are mounted at /shared/services
SIB_PATHS = [
    "/shared/services/api-gateway",
    "/shared/services/execution",
    "/shared/services/strategy-core"
]
for p in SIB_PATHS:
    if os.path.exists(p) and p not in sys.path:
        sys.path.insert(0, p)

# Try to import models from other services if they exist (for autogenerate)
try:
    from app.models import user, trade, strategy, strategy_run, risk_rule, signal_log, plugins, mental_hand_history
except ImportError:
    # Fallback/Log if not available in this environment
    print("Warning: Some service models could not be imported for autogenerate")

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    version_table = config.get_main_option("version_table", "alembic_version")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=version_table
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=DATABASE_URL
    )

    with connectable.connect() as connection:
        version_table = config.get_main_option("version_table", "alembic_version")
        context.configure(
            connection=connection, 
            target_metadata=target_metadata,
            version_table=version_table
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
