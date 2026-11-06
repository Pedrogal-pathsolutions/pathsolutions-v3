"""The worker's SQL against a throwaway cluster with the real schema, as pathsol_worker.

Runs in the API test image, which has PostgreSQL 18, with the API's migrations and test cluster mounted:

    docker run --rm --network none -v "$PWD/services/worker/src:/worker:ro" \
        -v "$PWD/services/worker/tests:/wtests:ro" -v "$PWD/services/api/src:/api:ro" \
        -v "$PWD/services/api/tests:/atests:ro" -e PYTHONPATH=/worker:/wtests:/api:/atests \
        pathsol-api-teste:<tag> python -m unittest discover -s /wtests -p 'test_banco.py'
"""
import dataclasses
import datetime
import time
import unittest
import uuid

import psycopg

from pathsol_worker import banco, consumidor, fila
from pathsol_worker.mensagem import Message

try:
    from cluster import Cluster
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste da API") from None

SHA = "c" * 64
H5_HASH = "0123456789ab"
LONG_AGO = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)


def completed(job):
    return consumidor.Completed(f"{job.tenant_id}/{job.slide_id}/{H5_HASH}/{job.id}.h5", 1024, SHA, "v1")


class Queue:
    """A queue that keeps what the worker did with each message."""

    def __init__(self):
        self.calls = []

    def put(self, text):
        self.calls.append(("put", text))

    def delete(self, received):
        self.calls.append(("delete", received.id))

    def update(self, received, visibility_timeout, text):
        self.calls.append(("update", visibility_timeout, text))


class Store(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cluster = Cluster()
        cls.cluster.create_schema()
        cls.cluster.psql("alter role pathsol_worker login")
        cls.db = cls.cluster.connect()
        cls.tenants = {}
        for slug in ("publico", "diagnose"):
            tenant = uuid.uuid4()
            cls.db.execute("insert into tenants (id, slug) values (%s, %s)", (tenant, slug))
            cls.tenants[slug] = tenant
        cls.store = banco.JobStore(f"host={cls.cluster.dir} user=pathsol_worker dbname=pathsol")

    @classmethod
    def tearDownClass(cls):
        cls.store.close()
        cls.db.close()
        cls.cluster.stop()

    def new_job(self, slug="publico", status="QUEUED"):
        tenant, slide, job = self.tenants[slug], uuid.uuid4(), uuid.uuid4()
        self.db.execute(
            "insert into slides (tenant_id, id, wsi_name, wsi_sha256, organ, material, stain) "
            "values (%s, %s, %s, %s, 'estomago', 'biopsia', 'HE')",
            (tenant, slide, f"{slide}.svs", SHA),
        )
        self.db.execute("insert into jobs (tenant_id, id, slide_id, status, pipeline_version) values (%s, %s, %s, %s, 'teste')",
                        (tenant, job, slide, status))
        return Message(job, tenant, slide, f"wsi-{slug}", f"{slide}.svs", "estomago", "biopsia", "teste", 0)

    def row(self, message):
        return self.db.execute("select status, reason, attempt, h5_blob from jobs where id = %s", (message.job_id,)).fetchone()

    def own_store(self):
        """A store whose backend cut() ends; the shared one keeps its connection."""
        store = banco.JobStore(f"host={self.cluster.dir} user=pathsol_worker dbname=pathsol application_name=corte")
        self.addCleanup(store.close)
        return store

    def cut(self):
        """Ends the backend of own_store(), as a database restart does."""
        self.db.execute("select pg_terminate_backend(pid, 5000) from pg_stat_activity where application_name = 'corte'")

    def set_finished_at(self, when):
        self.db.execute("insert into worker_heartbeat (worker, beat_at, finished_at) values ('vm2', now(), %s) "
                        "on conflict (worker) do update set finished_at = excluded.finished_at", (when,))

    def finished_age(self):
        return self.db.execute("select extract(epoch from now() - finished_at) from worker_heartbeat").fetchone()[0]

    def deliver(self, store, message, process, times=1):
        """Hands the message to the consumer `times` times, as the queue would; returns the results and both queues."""
        jobs, dead = Queue(), Queue()
        results = [consumidor.handle(fila.Received(f"m{n}", "pop", message.dumps(), n + 1), jobs, dead, store, process)
                   for n in range(times)]
        return results, jobs, dead

    def test_a_cut_connection_fails_one_call_and_the_next_one_reconnects(self):
        store, message = self.own_store(), self.new_job()
        store.beat()
        self.cut()
        with self.assertRaises(banco.Unavailable) as raised:
            store.claim(message)
        self.assertIsInstance(raised.exception.__cause__, psycopg.OperationalError)
        self.assertEqual(store.claim(message).status, "RUNNING")
        self.assertEqual(self.row(message)[0], "RUNNING")

    def test_an_outage_before_the_outcome_is_written_is_never_counted(self):
        store, message, times = self.own_store(), self.new_job(), banco.MAX_ATTEMPTS + 2

        def cut_then_complete(job):
            self.cut()
            return completed(job)

        results, jobs, dead = self.deliver(store, message, cut_then_complete, times)
        self.assertEqual(results, ["banco indisponível"] * times)
        self.assertEqual(dead.calls, [])
        self.assertEqual(jobs.calls, [("update", 60, message.dumps())] * times)
        self.assertEqual(self.row(message)[2], 0)
        self.set_finished_at(LONG_AGO)
        results, jobs, dead = self.deliver(store, message, completed)
        self.assertEqual((results, jobs.calls, dead.calls), (["COMPLETED"], [("delete", "m0")], []))
        self.assertEqual(self.row(message)[:3], ("COMPLETED", None, 0))
        self.assertLess(self.finished_age(), 5)

    def test_a_failure_while_the_database_is_down_is_never_counted(self):
        store, message, times = self.own_store(), self.new_job(), banco.MAX_ATTEMPTS + 2

        def cut_then_fail(job):
            self.cut()
            raise RuntimeError("falha técnica")

        results, jobs, dead = self.deliver(store, message, cut_then_fail, times)
        self.assertEqual(results, ["banco indisponível"] * times)
        self.assertEqual(dead.calls, [])
        self.assertEqual(jobs.calls, [("update", 60, message.dumps())] * times)
        self.assertEqual(self.row(message)[:3], ("RUNNING", None, 0))

    def test_beat_keeps_one_fresh_row_that_the_reconciler_reads(self):
        self.store.beat()
        first = self.db.execute("select beat_at from worker_heartbeat where worker = 'vm2'").fetchone()[0]
        self.store.beat()
        rows = self.db.execute("select worker, beat_at from worker_heartbeat").fetchall()
        self.assertEqual(len(rows), 1)
        self.assertGreater(rows[0][1], first)
        age = self.db.execute("select extract(epoch from now() - max(beat_at))::bigint from worker_heartbeat").fetchone()[0]
        self.assertLess(age, 5)

    def test_claim_runs_the_job_with_the_database_values(self):
        message = self.new_job()
        job = self.store.claim(message)
        self.assertEqual(job.status, "RUNNING")
        self.assertEqual((job.container, job.blob_name, job.wsi_sha256, job.stain), (message.container, message.blob_name, SHA, "HE"))
        self.assertEqual(self.row(message)[0], "RUNNING")

    def test_forged_tenant_finds_nothing_and_changes_nothing(self):
        message = self.new_job("diagnose")
        forged = dataclasses.replace(message, tenant_id=self.tenants["publico"], container="wsi-publico")
        self.assertIsNone(self.store.claim(forged))
        self.assertEqual(self.row(message)[0], "QUEUED")

    def test_message_that_disagrees_with_the_database_is_refused(self):
        message = self.new_job()
        for change in ({"material": "peca"}, {"organ": None}, {"container": "wsi-diagnose"},
                       {"slide_id": uuid.uuid4()}, {"blob_name": f"{message.slide_id}.tif"}):
            with self.subTest(change=change):
                self.assertIsNone(self.store.claim(dataclasses.replace(message, **change)))
        self.assertEqual(self.row(message)[0], "QUEUED")

    def test_finished_job_is_returned_untouched(self):
        message = self.new_job()
        job = self.store.claim(message)
        h5 = f"{job.tenant_id}/{job.slide_id}/{H5_HASH}/{job.id}.h5"
        self.store.complete(job, h5, 1024, SHA, "v1")
        again = self.store.claim(message)
        self.assertEqual(again.status, "COMPLETED")
        self.assertEqual(self.row(message), ("COMPLETED", None, 0, h5))

    def test_job_running_after_a_deallocation_runs_again_without_counting(self):
        message = self.new_job()
        self.store.claim(message)
        self.assertEqual(self.store.claim(message).status, "RUNNING")
        self.assertEqual(self.row(message)[2], 0)

    def test_finishing_twice_is_refused(self):
        message = self.new_job()
        job = self.store.claim(message)
        self.store.unsupported(job, "scale_unavailable")
        with self.assertRaises(banco.StateError):
            self.store.qc_failed(job, "empty_glass")
        self.assertEqual(self.row(message)[:2], ("UNSUPPORTED_FORMAT", "scale_unavailable"))

    def test_every_terminal_state_records_when_a_job_finished(self):
        finishes = {
            "COMPLETED": lambda job: self.store.complete(job, f"{job.tenant_id}/{job.slide_id}/{H5_HASH}/{job.id}.h5",
                                                         1024, SHA, "v1"),
            "QC_FAILED": lambda job: self.store.qc_failed(job, "empty_glass"),
            "UNSUPPORTED_FORMAT": lambda job: self.store.unsupported(job, "scale_unavailable"),
            "DEAD_LETTER": self.store.dead_letter,
        }
        for state, finish in finishes.items():
            with self.subTest(state=state):
                self.set_finished_at(LONG_AGO)
                message = self.new_job()
                finish(self.store.claim(message))
                self.assertEqual(self.row(message)[0], state)
                self.assertLess(self.finished_age(), 5)

    def test_a_refused_finish_keeps_the_last_finish_time(self):
        job = self.store.claim(self.new_job())
        self.store.unsupported(job, "scale_unavailable")
        self.set_finished_at(LONG_AGO)
        with self.assertRaises(banco.StateError):
            self.store.qc_failed(job, "empty_glass")
        self.assertEqual(self.db.execute("select finished_at from worker_heartbeat").fetchone()[0], LONG_AGO)

    def test_focus_block_keeps_the_scores_pointer(self):
        message = self.new_job()
        job = self.store.claim(message)
        scores = f"{job.tenant_id}/{job.slide_id}/{H5_HASH}/{job.id}.qc.h5"
        self.store.qc_failed(job, "focus", scores)
        self.assertEqual(self.db.execute("select qc_scores_blob from jobs where id = %s", (job.id,)).fetchone()[0], scores)

    def test_technical_failures_count_and_the_last_one_stays_for_the_dead_letter(self):
        message = self.new_job()
        job = self.store.claim(message)
        self.assertEqual(self.store.failed(job), 1)
        self.assertEqual(self.row(message)[:3], ("QUEUED", None, 1))
        job = self.store.claim(message.with_attempt(1))
        self.assertEqual(self.store.failed(job), 2)
        job = self.store.claim(message.with_attempt(2))
        self.assertEqual(self.store.failed(job), banco.MAX_ATTEMPTS)
        self.assertEqual(self.row(message)[:3], ("RUNNING", None, 3))
        self.store.dead_letter(job)
        self.assertEqual(self.row(message)[:3], ("DEAD_LETTER", None, 3))


class Restart(unittest.TestCase):
    """The server stopped and started again, in a cluster of its own: the stop ends every connection."""

    @classmethod
    def setUpClass(cls):
        cls.cluster = Cluster()
        cls.cluster.create_schema()
        cls.cluster.psql("alter role pathsol_worker login")

    @classmethod
    def tearDownClass(cls):
        cls.cluster.stop()

    def store(self):
        store = banco.JobStore(f"host={self.cluster.dir} user=pathsol_worker dbname=pathsol")
        self.addCleanup(store.close)
        return store

    def test_with_the_server_stopped_calls_fail_fast_and_work_once_it_starts(self):
        connected = self.store()
        connected.beat()
        self.cluster.shutdown()
        try:
            started = time.monotonic()
            with self.assertRaises(banco.Unavailable):
                connected.beat()  # the connection the shutdown ended
            with self.assertRaises(banco.Unavailable):
                connected.beat()  # a new one, refused
            built = self.store()  # as the worker starting with the database down
            with self.assertRaises(banco.Unavailable):
                built.beat()
            self.assertLess(time.monotonic() - started, 5)
        finally:
            self.cluster.start()
        connected.beat()
        built.beat()
        with self.cluster.connect() as db:
            age = db.execute("select extract(epoch from now() - beat_at) from worker_heartbeat").fetchone()[0]
        self.assertLess(age, 5)

    def test_a_store_that_never_connected_closes(self):
        store = banco.JobStore("host=/nenhum user=pathsol_worker dbname=pathsol")
        with self.assertRaises(banco.Unavailable):
            store.beat()
        store.close()  # main() closes it even when the database never answered


if __name__ == "__main__":
    unittest.main()
