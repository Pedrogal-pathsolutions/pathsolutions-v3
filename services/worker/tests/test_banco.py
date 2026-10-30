"""The worker's SQL against a throwaway cluster with the real schema, as pathsol_worker.

Runs in the API test image, which has PostgreSQL 18 and the migrations:

    docker run --rm --network none -v "$PWD/services/worker/src:/worker:ro" \
        -v "$PWD/services/worker/tests:/wtests:ro" \
        -e PYTHONPATH=/worker:/wtests:/src/services/api/tests pathsol-api-teste:<tag> \
        python -m unittest discover -s /wtests -p 'test_banco.py'
"""
import dataclasses
import unittest
import uuid

from pathsol_worker import banco
from pathsol_worker.mensagem import Message

try:
    from cluster import Cluster
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste da API") from None

SHA = "c" * 64
H5_HASH = "0123456789ab"


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


if __name__ == "__main__":
    unittest.main()
