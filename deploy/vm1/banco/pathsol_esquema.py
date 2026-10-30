#!/usr/bin/python3
"""Creates and migrates the v3 database inside its container (plan, section 7).

    pathsol_esquema.py pathsol-api:<commit>

The SQL comes from the API image, run with no network (pathsol_api.esquema).
psql applies it as the superuser, inside pathsol-banco: first the roles and
the database, then the migrations from the revision the database is at. It
stops at the first error, and the migrations run in one transaction.
"""
import re
import subprocess
import sys

DATABASE = "pathsol-banco"
IMAGE = re.compile(r"^pathsol-api:[0-9a-f]{7,40}$")


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def sql_from(image, *args):
    return run(["docker", "run", "--rm", "--network", "none", image, "python", "-m", "pathsol_api.esquema", *args]).stdout


def psql(sql, db):
    run(["docker", "exec", "-i", "-u", "postgres", DATABASE, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", db], input=sql)


def query(sql):
    args = ["docker", "exec", "-u", "postgres", DATABASE, "psql", "-XAtq", "-v", "ON_ERROR_STOP=1", "-d", "pathsol", "-c", sql]
    return run(args).stdout.strip()


def revision():
    if query("select to_regclass('public.alembic_version') is not null") != "t":
        return None
    return query("select version_num from alembic_version")


def apply(image):
    psql(sql_from(image, "papeis"), "postgres")
    before = revision()
    psql(sql_from(image, "migracao", *(["--de", before] if before else [])), "pathsol")
    return before, revision()


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1 or not IMAGE.match(argv[0]):
        sys.exit("uso: pathsol_esquema.py pathsol-api:<commit>")
    try:
        before, after = apply(argv[0])
    except subprocess.CalledProcessError as error:
        sys.exit(f"FALHA: {' '.join(error.cmd[:6])}: {error.stderr.strip()}")
    print(f"OK esquema: revisão {before or 'nenhuma'} -> {after}")


if __name__ == "__main__":
    main()
