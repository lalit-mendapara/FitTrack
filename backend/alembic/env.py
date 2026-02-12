from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Import ALL models so Alembic sees them ---
from app.database import Base
import app.models  # triggers __init__.py which imports all models

target_metadata = Base.metadata

# --- Get DB URL from the same env var the app uses ---
from config import SQLALCHEMY_DATABASE_URL
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Tables to ignore during autogenerate (legacy Django tables still in DB)
EXCLUDE_TABLES = {
    "auth_user", "auth_group", "auth_permission",
    "auth_user_groups", "auth_user_user_permissions",
    "auth_group_permissions", "django_admin_log",
    "django_content_type", "django_migrations", "django_session",
}

def include_object(object, name, type_, reflected, compare_to):
    """Exclude legacy Django tables from Alembic autogenerate."""
    if type_ == "table" and name in EXCLUDE_TABLES:
        return False
    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
