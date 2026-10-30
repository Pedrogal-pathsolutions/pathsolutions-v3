"""SQL that creates and migrates the v3 database (plan, section 7; skill pathsol-isolamento-tenant).

Only the superuser changes the database, inside its container, by psql: first
the roles and the database (cluster level, idempotent), then the Alembic
offline SQL, run as the owner role so that every object belongs to it.

    python -m pathsol_api.esquema papeis
    python -m pathsol_api.esquema migracao [--de REVISAO]
"""
import argparse
import io
import os

from alembic import command
from alembic.config import Config

ALEMBIC_INI = os.path.join(os.path.dirname(__file__), "alembic.ini")
OWNER = "pathsol_dono"

ROLES_SQL = r"""
-- The owner never logs in: migrations take it with SET ROLE.
SELECT 'CREATE ROLE pathsol_dono NOLOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pathsol_dono') \gexec
-- The worker on VM2; it gets LOGIN and a password with the consumer (slice 5).
SELECT 'CREATE ROLE pathsol_worker NOLOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pathsol_worker') \gexec
-- Decision 7: the test producer, taken only with SET ROLE by the operator on VM1; leaves in Phase 5.
SELECT 'CREATE ROLE pathsol_produtor NOLOGIN' WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'pathsol_produtor') \gexec
SELECT 'CREATE DATABASE pathsol OWNER pathsol_dono' WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'pathsol') \gexec
REVOKE ALL ON DATABASE pathsol FROM PUBLIC;
GRANT CONNECT ON DATABASE pathsol TO pathsol_worker;
"""


def roles_sql():
    return ROLES_SQL


def upgrade_sql(current=None):
    """Alembic offline SQL from `current` (None for an empty database) to the last revision."""
    buffer = io.StringIO()
    command.upgrade(Config(ALEMBIC_INI, output_buffer=buffer), f"{current}:head" if current else "head", sql=True)
    return buffer.getvalue()


def as_owner(sql):
    return f"SET ROLE {OWNER};\n{sql}"


def main(argv=None):
    parser = argparse.ArgumentParser(description="SQL do banco da v3, para o psql do superusuário.")
    commands = parser.add_subparsers(dest="comando", required=True)
    commands.add_parser("papeis", help="papéis e banco (no banco postgres)")
    migration = commands.add_parser("migracao", help="migrações até a última (no banco pathsol)")
    migration.add_argument("--de", help="revisão atual do banco; sem ela, desde o banco vazio")
    args = parser.parse_args(argv)
    print(roles_sql() if args.comando == "papeis" else as_owner(upgrade_sql(args.de)))


if __name__ == "__main__":
    main()
