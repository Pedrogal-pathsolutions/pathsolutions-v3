import os
import subprocess
import unittest
import uuid
from contextlib import closing

import psycopg
from psycopg import errors

from cluster import Cluster

A, B = uuid.uuid4(), uuid.uuid4()
SHA = "0" * 64


def slide_row():
    slide = uuid.uuid4()
    return slide, f"{slide}.svs"


class Schema(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cluster = Cluster()
        cls.cluster.create_schema()
        cls.db = cls.cluster.connect()
        cls.slides, cls.jobs = {}, {}
        for tenant, slug in ((A, "diagnose"), (B, "publico")):
            cls.db.execute("insert into tenants (id, slug) values (%s, %s)", (tenant, slug))
            slide, blob = slide_row()
            cls.db.execute(
                "insert into slides (tenant_id, id, wsi_name, wsi_sha256, material, stain) values (%s, %s, %s, %s, 'biopsia', 'HE')",
                (tenant, slide, blob, SHA),
            )
            job = uuid.uuid4()
            cls.db.execute(
                "insert into jobs (tenant_id, id, slide_id, pipeline_version) values (%s, %s, %s, 'teste')",
                (tenant, job, slide),
            )
            cls.slides[tenant], cls.jobs[tenant] = slide, job

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.cluster.stop()

    def as_role(self, role, tenant=None):
        """A transaction as `role`, with the tenant set the way the API and the worker set it."""
        conn = self.cluster.connect()
        conn.autocommit = False
        self.addCleanup(conn.close)
        # A grant too wide must fail the test, not leave the next one waiting on a row lock.
        conn.execute("set lock_timeout = '2s'")
        conn.execute(f"set role {role}")
        if tenant is not None:
            conn.execute("select set_config('app.tenant_id', %s, true)", (str(tenant),))
        return conn

    def count(self, conn, table):
        return conn.execute(f"select count(*) from {table}").fetchone()[0]

    def test_rls_enabled_and_forced_on_every_tenant_table(self):
        rows = self.db.execute(
            "select relname, relrowsecurity, relforcerowsecurity from pg_class "
            "where relname in ('tenants', 'slides', 'jobs') order by relname"
        ).fetchall()
        self.assertEqual(rows, [("jobs", True, True), ("slides", True, True), ("tenants", True, True)])

    def test_application_roles_are_not_owners_and_cannot_bypass(self):
        roles = self.db.execute(
            "select rolname, rolsuper, rolbypassrls, rolcanlogin from pg_roles where rolname like 'pathsol\\_%' order by rolname"
        ).fetchall()
        self.assertEqual(
            roles,
            [("pathsol_dono", False, False, False), ("pathsol_produtor", False, False, False), ("pathsol_worker", False, False, False)],
        )
        owners = {r[0] for r in self.db.execute("select tableowner from pg_tables where schemaname = 'public'")}
        self.assertEqual(owners, {"pathsol_dono"})

    def test_no_tenant_reads_nothing(self):
        # Isolation test 3 of the skill.
        for role in ("pathsol_worker", "pathsol_produtor"):
            conn = self.as_role(role)
            for table in ("tenants", "slides", "jobs"):
                if role == "pathsol_produtor" and table != "tenants":
                    continue
                with self.subTest(role=role, table=table):
                    self.assertEqual(self.count(conn, table), 0)

    def test_tenant_left_by_a_finished_transaction_reads_nothing(self):
        conn = self.as_role("pathsol_worker", A)
        conn.commit()
        self.assertEqual(self.count(conn, "jobs"), 0)

    def test_each_tenant_sees_only_its_rows(self):
        conn = self.as_role("pathsol_worker", A)
        self.assertEqual([r[0] for r in conn.execute("select id from jobs")], [self.jobs[A]])
        self.assertEqual([r[0] for r in conn.execute("select id from slides")], [self.slides[A]])
        self.assertEqual([r[0] for r in conn.execute("select id from tenants")], [A])

    def test_producer_cannot_write_into_another_tenant(self):
        conn = self.as_role("pathsol_produtor", A)
        slide, blob = slide_row()
        with self.assertRaises(errors.InsufficientPrivilege):
            conn.execute(
                "insert into slides (tenant_id, id, wsi_name, wsi_sha256, material, stain) values (%s, %s, %s, %s, 'biopsia', 'HE')",
                (B, slide, blob, SHA),
            )

    def test_producer_reads_only_the_slides_of_its_tenant(self):
        conn = self.as_role("pathsol_produtor", A)
        self.assertEqual([r[0] for r in conn.execute("select id from slides")], [self.slides[A]])
        with self.assertRaises(errors.InsufficientPrivilege):
            conn.execute("select id from jobs")

    def test_producer_writes_into_its_tenant(self):
        conn = self.as_role("pathsol_produtor", A)
        slide, blob = slide_row()
        conn.execute(
            "insert into slides (tenant_id, id, wsi_name, wsi_sha256, material, stain) values (%s, %s, %s, %s, 'peca', 'HE')",
            (A, slide, blob, SHA),
        )
        conn.execute("insert into jobs (tenant_id, id, slide_id, pipeline_version) values (%s, %s, %s, 'teste')", (A, uuid.uuid4(), slide))
        conn.rollback()

    def test_job_cannot_point_to_a_slide_of_another_tenant(self):
        with self.assertRaises(errors.ForeignKeyViolation):
            self.db.execute(
                "insert into jobs (tenant_id, id, slide_id, pipeline_version) values (%s, %s, %s, 'teste')",
                (A, uuid.uuid4(), self.slides[B]),
            )

    def test_worker_cannot_delete_insert_or_move_a_job(self):
        statements = (
            ("delete from jobs", ()),
            ("insert into jobs (tenant_id, id, slide_id, pipeline_version) values (%s, %s, %s, 'x')", (A, uuid.uuid4(), self.slides[A])),
            ("update jobs set slide_id = slide_id", ()),
            ("update jobs set tenant_id = tenant_id", ()),
            ("update slides set wsi_name = wsi_name", ()),
        )
        for sql, args in statements:
            with self.subTest(sql=sql), closing(self.as_role("pathsol_worker", A)) as conn:
                with self.assertRaises(errors.InsufficientPrivilege):
                    conn.execute(sql, args)

    def test_worker_moves_a_job_of_its_tenant_through_the_states(self):
        conn = self.as_role("pathsol_worker", A)
        done = conn.execute(
            "update jobs set status = 'QC_FAILED', reason = 'focus', attempt = attempt + 1, updated_at = now(), "
            "qc_scores_blob = tenant_id || '/' || slide_id || '/abc123def456/' || id || '.qc.h5' where id = %s",
            (self.jobs[A],),
        ).rowcount
        self.assertEqual(done, 1)
        self.assertEqual(conn.execute("update jobs set attempt = 1 where id = %s", (self.jobs[B],)).rowcount, 0)
        conn.rollback()

    def test_reason_must_match_the_state(self):
        bad = (
            ("QC_FAILED", None), ("QC_FAILED", "format"), ("UNSUPPORTED_FORMAT", "focus"),
            ("UNSUPPORTED_FORMAT", None), ("QUEUED", "focus"), ("DEAD_LETTER", "empty_glass"),
        )
        for status, reason in bad:
            with self.subTest(status=status, reason=reason), self.assertRaises(errors.CheckViolation):
                self.db.execute("update jobs set status = %s, reason = %s where id = %s", (status, reason, self.jobs[A]))
        for status, reason in (("UNSUPPORTED_FORMAT", "scale_unavailable"), ("QC_FAILED", "empty_glass"), ("RUNNING", None)):
            with self.subTest(status=status, reason=reason):
                self.db.execute("update jobs set status = %s, reason = %s where id = %s", (status, reason, self.jobs[A]))
        self.db.execute("update jobs set status = 'QUEUED', reason = null where id = %s", (self.jobs[A],))

    def test_completed_has_the_pointer_and_only_then(self):
        job = self.jobs[A]
        h5 = f"{A}/{self.slides[A]}/abc123def456/{job}.h5"
        with self.assertRaises(errors.CheckViolation):
            self.db.execute("update jobs set status = 'COMPLETED' where id = %s", (job,))
        with self.assertRaises(errors.CheckViolation):
            self.db.execute("update jobs set h5_blob = %s, h5_size = 1, h5_sha256 = %s, extractor_version = 'v' where id = %s", (h5, SHA, job))
        self.db.execute(
            "update jobs set status = 'COMPLETED', h5_blob = %s, h5_size = 1, h5_sha256 = %s, extractor_version = 'v' where id = %s",
            (h5, SHA, job),
        )
        self.db.execute("update jobs set status = 'QUEUED', h5_blob = null, h5_size = null, h5_sha256 = null, extractor_version = null where id = %s", (job,))

    def test_pointer_starts_with_its_own_tenant_and_slide(self):
        job = self.jobs[A]
        for h5 in (f"{B}/{self.slides[A]}/abc123def456/{job}.h5", f"{A}/{self.slides[B]}/abc123def456/{job}.h5", f"{A}/{self.slides[A]}/x/{uuid.uuid4()}.h5"):
            with self.subTest(h5=h5), self.assertRaises(errors.CheckViolation):
                self.db.execute(
                    "update jobs set status = 'COMPLETED', h5_blob = %s, h5_size = 1, h5_sha256 = %s, extractor_version = 'v' where id = %s",
                    (h5, SHA, job),
                )

    def test_wsi_name_is_the_slide_uuid_never_the_original_name(self):
        slide = uuid.uuid4()
        for blob in ("caso-12345.svs", f"{uuid.uuid4()}.svs", f"wsi-diagnose/{slide}.svs", f"{slide}"):
            with self.subTest(blob=blob), self.assertRaises(errors.CheckViolation):
                self.db.execute(
                    "insert into slides (tenant_id, id, wsi_name, wsi_sha256, material, stain) values (%s, %s, %s, %s, 'biopsia', 'HE')",
                    (A, slide, blob, SHA),
                )

    def test_dump_restores_like_the_monthly_restore_test(self):
        # deploy/vm1/banco/pathsol_banco.py: globais.sql, then pg_restore --create --exit-on-error of each dump.
        dump = os.path.join(self.cluster.dir, "pathsol.dump")
        source = ["-h", self.cluster.dir, "-U", "postgres"]
        subprocess.run(["pg_dump", *source, "--format=custom", "--compress=zstd", f"--file={dump}", "--dbname=pathsol"], check=True)
        roles = subprocess.run(["pg_dumpall", *source, "--globals-only"], check=True, capture_output=True, text=True).stdout
        other = Cluster()
        self.addCleanup(other.stop)
        # The restore test tolerates the repeated CREATE ROLE postgres, as here.
        subprocess.run(["psql", "-X", "-q", "-h", other.dir, "-U", "postgres", "-d", "postgres"], input=roles, text=True, capture_output=True)
        subprocess.run(["pg_restore", "-h", other.dir, "-U", "postgres", "--exit-on-error", "--create", "--dbname=postgres", dump], check=True)
        with closing(psycopg.connect(host=other.dir, user="postgres", dbname="pathsol")) as conn:
            rows = conn.execute(
                "select relname, relforcerowsecurity, pg_get_userbyid(relowner) from pg_class "
                "where relname in ('jobs', 'slides', 'tenants') order by relname"
            ).fetchall()
        self.assertEqual(rows, [("jobs", True, "pathsol_dono"), ("slides", True, "pathsol_dono"), ("tenants", True, "pathsol_dono")])

    def test_unknown_material_is_refused(self):
        slide = uuid.uuid4()
        with self.assertRaises(errors.CheckViolation):
            self.db.execute(
                "insert into slides (tenant_id, id, wsi_name, wsi_sha256, material, stain) values (%s, %s, %s, %s, 'congelacao', 'HE')",
                (A, slide, f"{slide}.svs", SHA),
            )


if __name__ == "__main__":
    unittest.main()
