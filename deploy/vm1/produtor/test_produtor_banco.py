"""The producer's SQL against a throwaway cluster with the real schema.

Runs in the API test image, which has PostgreSQL 18 and the schema:

    docker run --rm --network none -v "$PWD/deploy/vm1/produtor:/produtor:ro" \
        -e PYTHONPATH=/produtor:/src/services/api/tests pathsol-api-teste:<tag> \
        python -m unittest discover -s /produtor -p 'test_produtor_banco.py'
"""
import subprocess
import unittest
import uuid
from unittest import mock

import pathsol_produtor as produtor

try:
    from cluster import Cluster
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste da API") from None

PREFIX = ["docker", "exec", "-i", "-u", "postgres", "pathsol-banco"]


class ProducerSql(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cluster = Cluster()
        cls.cluster.create_schema()

    @classmethod
    def tearDownClass(cls):
        cls.cluster.stop()

    def local(self, args, **kwargs):
        self.assertEqual(args[:6], PREFIX)
        return subprocess.run([*args[6:], "-h", self.cluster.dir, "-U", "postgres"], check=True, capture_output=True, text=True, **kwargs)

    def psql(self, sql, **variables):
        with mock.patch.object(produtor, "run", self.local):
            return produtor.psql(sql, **variables)

    def slide(self, slug):
        slide = str(uuid.uuid4())
        self.psql(produtor.SLIDE_SQL, slug=slug, slide=slide, nome=f"{slide}.svs", sha256="b" * 64,
                  material="biopsia", coloracao="HE", orgao="estomago")
        return slide

    def test_tenant_is_created_once(self):
        first = self.psql(produtor.TENANT_SQL, id=uuid.uuid4(), slug="publico")
        again = self.psql(produtor.TENANT_SQL, id=uuid.uuid4(), slug="publico")
        self.assertEqual(first, again)

    def test_job_of_a_registered_slide(self):
        tenant = self.psql(produtor.TENANT_SQL, id=uuid.uuid4(), slug="publico")
        slide = self.slide("publico")
        job = str(uuid.uuid4())
        out = self.psql(produtor.JOB_SQL, slug="publico", slide=slide, job=job, versao="teste")
        self.assertEqual(out, f"{tenant}|{slide}.svs|estomago|biopsia")
        with self.cluster.connect() as db:
            row = db.execute("select tenant_id::text, slide_id::text, status, attempt from jobs where id = %s", (job,)).fetchone()
        self.assertEqual(row, (tenant, slide, "QUEUED", 0))

    def test_job_for_a_slide_of_another_tenant_is_refused(self):
        self.psql(produtor.TENANT_SQL, id=uuid.uuid4(), slug="publico")
        self.psql(produtor.TENANT_SQL, id=uuid.uuid4(), slug="diagnose")
        other = self.slide("diagnose")
        job = str(uuid.uuid4())
        with self.assertRaises(subprocess.CalledProcessError):
            self.psql(produtor.JOB_SQL, slug="publico", slide=other, job=job, versao="teste")
        with self.cluster.connect() as db:
            self.assertIsNone(db.execute("select 1 from jobs where id = %s", (job,)).fetchone())

    def test_unknown_tenant_is_refused(self):
        with self.assertRaises(subprocess.CalledProcessError):
            self.slide("naoexiste")


if __name__ == "__main__":
    unittest.main()
