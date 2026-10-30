"""A throwaway PostgreSQL 18 cluster on a socket in a temporary directory.

The schema reaches it by the same path as production: the role SQL and the
Alembic offline SQL, applied with psql by the superuser.
"""
import os
import shutil
import subprocess
import tempfile

import psycopg

from pathsol_api import esquema

BIN = "/usr/lib/postgresql/18/bin"


class Cluster:
    def __init__(self):
        self.dir = tempfile.mkdtemp(prefix="pg-")
        self.data = os.path.join(self.dir, "data")
        subprocess.run(
            [f"{BIN}/initdb", "-D", self.data, "-U", "postgres", "--auth=trust", "--encoding=UTF8",
             "--locale=C.UTF-8", "--locale-provider=builtin", "--builtin-locale=C.UTF-8"],
            check=True, capture_output=True,
        )
        subprocess.run(
            [f"{BIN}/pg_ctl", "-D", self.data, "-w", "-l", os.path.join(self.dir, "log"),
             "-o", f"-k {self.dir} -c listen_addresses=''", "start"],
            check=True, capture_output=True,
        )

    def psql(self, sql, db="postgres"):
        return subprocess.run(
            ["psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", self.dir, "-U", "postgres", "-d", db],
            input=sql, text=True, check=True, capture_output=True,
        ).stdout

    def create_schema(self):
        self.psql(esquema.roles_sql())
        self.psql(esquema.as_owner(esquema.upgrade_sql()), db="pathsol")

    def connect(self):
        return psycopg.connect(host=self.dir, user="postgres", dbname="pathsol", autocommit=True)

    def stop(self):
        subprocess.run([f"{BIN}/pg_ctl", "-D", self.data, "-m", "immediate", "stop"], capture_output=True)
        shutil.rmtree(self.dir, ignore_errors=True)
