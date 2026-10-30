"""Offline only: the SQL is applied by the superuser inside the database container (pathsol_api.esquema)."""
from alembic import context

if not context.is_offline_mode():
    raise SystemExit("só modo offline: o SQL é aplicado pelo superusuário, dentro do container do banco")

context.configure(url="postgresql+psycopg://", literal_binds=True)
with context.begin_transaction():
    context.run_migrations()
