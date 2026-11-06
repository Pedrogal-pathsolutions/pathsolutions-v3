"""The worker's side of the jobs table (plan, section 9.1; skill pathsol-isolamento-tenant).

Each transaction sets the message's tenant with set_config(..., true), so RLS
keeps it to that tenant's rows: a forged message finds no job. The role,
pathsol_worker, reads jobs and slides and moves only the state columns, and
every change requires the job to be RUNNING, so a duplicate delivery never
finishes a job twice.

A database that does not answer (psycopg.OperationalError: connection refused
or lost, server shutting down) raises Unavailable, no failure of the job
(Pedro, 06/11). The store connects on its first call, so the worker starts
with the database down, and again on the call after an outage; the call that
met the outage is not retried.
"""
import contextlib
import dataclasses
import uuid

import psycopg

MAX_ATTEMPTS = 3
TERMINAL = ("COMPLETED", "QC_FAILED", "UNSUPPORTED_FORMAT", "DEAD_LETTER")

CLAIM = """
select j.status, j.attempt, s.id, 'wsi-' || t.slug, s.wsi_name, s.wsi_sha256, s.organ, s.material, s.stain
from jobs j
join slides s on s.tenant_id = j.tenant_id and s.id = j.slide_id
join tenants t on t.id = j.tenant_id
where j.id = %s
"""


class StateError(Exception):
    """The job was not RUNNING: another delivery already moved it."""


class Unavailable(Exception):
    """The database did not answer: the job is not to blame."""


@dataclasses.dataclass(frozen=True)
class Job:
    id: uuid.UUID
    tenant_id: uuid.UUID
    slide_id: uuid.UUID
    container: str
    blob_name: str
    wsi_sha256: str
    organ: str | None
    material: str
    stain: str
    status: str
    attempt: int


class JobStore:
    def __init__(self, conninfo, **params):
        self.conninfo, self.params = conninfo, params
        self.conn = None

    @contextlib.contextmanager
    def _connection(self):
        try:
            if self.conn is None or self.conn.closed:
                # Autocommit: each transaction() block is the whole transaction, with nothing implicit around it.
                # The password comes in params, never in the conninfo, which may be logged.
                # The timeouts turn a VM1 that vanished into an error within about a minute, never a hung worker.
                self.conn = psycopg.connect(self.conninfo, autocommit=True, connect_timeout=10, keepalives_idle=30,
                                            keepalives_interval=10, keepalives_count=3, tcp_user_timeout=30000,
                                            **self.params)
            yield self.conn
        except psycopg.OperationalError as error:
            raise Unavailable(str(error)) from error

    def close(self):
        if self.conn is not None:
            self.conn.close()

    def beat(self):
        """The heartbeat the reconciler reads (plan 8.3, layer 3), in a table with no tenant data."""
        with self._connection() as conn:
            conn.execute("insert into worker_heartbeat (worker, beat_at) values ('vm2', now()) "
                         "on conflict (worker) do update set beat_at = excluded.beat_at")

    @contextlib.contextmanager
    def _tenant(self, tenant_id):
        with self._connection() as conn, conn.transaction():
            conn.execute("select set_config('app.tenant_id', %s, true)", (str(tenant_id),))
            yield conn

    def claim(self, message):
        """The message's job, now RUNNING; finished jobs come back as they are; None if it does not match the database."""
        with self._tenant(message.tenant_id) as conn:
            row = conn.execute(CLAIM, (message.job_id,)).fetchone()
            if row is None:
                return None
            status, attempt, slide, container, name, sha256, organ, material, stain = row
            seen = (message.slide_id, message.container, message.blob_name, message.organ, message.material)
            if seen != (slide, container, name, organ, material):
                return None
            job = Job(message.job_id, message.tenant_id, slide, container, name, sha256, organ, material, stain, status, attempt)
            if status in TERMINAL:
                return job
            conn.execute("update jobs set status = 'RUNNING', updated_at = now() where id = %s", (job.id,))
            return dataclasses.replace(job, status="RUNNING")

    def _finish(self, job, assignments, args):
        with self._tenant(job.tenant_id) as conn:
            sql = f"update jobs set {assignments}, updated_at = now() where id = %s and status = 'RUNNING'"
            if conn.execute(sql, (*args, job.id)).rowcount != 1:
                raise StateError(f"job {job.id} não estava RUNNING")
            # The reconciler stops starting VM2 after 3 starts in a row with no job finished (Pedro, 06/11).
            conn.execute("insert into worker_heartbeat (worker, beat_at, finished_at) values ('vm2', now(), now()) "
                         "on conflict (worker) do update set finished_at = excluded.finished_at")

    def complete(self, job, h5_blob, h5_size, h5_sha256, extractor_version):
        self._finish(job, "status = 'COMPLETED', h5_blob = %s, h5_size = %s, h5_sha256 = %s, extractor_version = %s",
                     (h5_blob, h5_size, h5_sha256, extractor_version))

    def qc_failed(self, job, reason, scores_blob=None):
        self._finish(job, "status = 'QC_FAILED', reason = %s, qc_scores_blob = %s", (reason, scores_blob))

    def unsupported(self, job, reason):
        self._finish(job, "status = 'UNSUPPORTED_FORMAT', reason = %s", (reason,))

    def dead_letter(self, job):
        self._finish(job, "status = 'DEAD_LETTER'", ())

    def failed(self, job):
        """Counts one technical failure; returns the count. Below the maximum the job waits QUEUED for the
        retry; at the maximum it stays RUNNING until the message is in the dead-letter queue (plan 9.1)."""
        with self._tenant(job.tenant_id) as conn:
            row = conn.execute(
                "update jobs set attempt = attempt + 1, updated_at = now(), "
                "status = case when attempt + 1 >= %s then status else 'QUEUED' end "
                "where id = %s and status = 'RUNNING' returning attempt",
                (MAX_ATTEMPTS, job.id),
            ).fetchone()
        if row is None:
            raise StateError(f"job {job.id} não estava RUNNING")
        return row[0]
