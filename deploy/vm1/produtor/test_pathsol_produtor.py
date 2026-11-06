import contextlib
import io
import json
import subprocess
import unittest
import uuid
from unittest import mock
from xml.etree import ElementTree

import pathsol_produtor as produtor

TENANT = str(uuid.uuid4())
SLIDE = str(uuid.uuid4())
JOB = str(uuid.uuid4())
SHA = "a" * 64
TOKEN = "eyJ0b2tlbi1kYS12bTEifQ"
# What the database gives back for an existing job: slide, pipeline version, then the values of "job".
STORED = f"{SLIDE}|fase4-teste|{TENANT}|{SLIDE}.svs|estomago|biopsia\n"


class Calls:
    """Fake docker (psql) and HTTP: answers in order and keeps what was sent."""

    def __init__(self, psql_out="", fail_send=False):
        self.psql_out = psql_out
        self.fail_send = fail_send
        self.log = []

    def run(self, args, **kwargs):
        self.log.append(("psql", args, kwargs.get("input")))
        return subprocess.CompletedProcess(args, 0, stdout=self.psql_out, stderr="")

    def open(self, request, timeout=None):
        url = request.full_url
        if url.startswith("http://169.254.169.254/"):
            self.log.append(("imds", url, None))
            return io.BytesIO(json.dumps({"access_token": TOKEN}).encode())
        self.log.append(("fila", request, request.data))
        if self.fail_send:
            raise produtor.urllib.error.URLError("sem rede")
        return io.BytesIO(b"")


def run_main(calls, *argv):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(produtor, "run", calls.run), mock.patch.object(produtor, "urlopen", calls.open), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = produtor.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


def sent_text(calls):
    """The text of the message that went to the queue."""
    return ElementTree.fromstring(calls.log[-1][2]).findtext("MessageText")


class Job(unittest.TestCase):
    def test_commits_in_the_database_before_sending_and_uses_its_values(self):
        calls = Calls(psql_out=f"{TENANT}|{SLIDE}.svs|estomago|biopsia\n")
        code, out, _ = run_main(calls, "job", "--tenant", "publico", "--lamina", SLIDE)
        self.assertEqual(code, 0)
        self.assertEqual([kind for kind, *_ in calls.log], ["psql", "imds", "fila"])
        _, args, sql = calls.log[0]
        self.assertEqual(args[:6], ["docker", "exec", "-i", "-u", "postgres", "pathsol-banco"])
        self.assertIn("SET LOCAL ROLE pathsol_produtor", sql)
        self.assertLess(sql.index("INSERT INTO jobs"), sql.index("COMMIT"))
        _, request, body = calls.log[2]
        self.assertTrue(request.full_url.startswith("https://pathsolwsiv3.queue.core.windows.net/jobs/messages?"))
        self.assertIn("messagettl=-1", request.full_url)
        self.assertEqual(request.get_method(), "POST")
        message = json.loads(ElementTree.fromstring(body).findtext("MessageText"))
        self.assertEqual(
            set(message), {"job_id", "tenant_id", "slide_id", "blob", "organ", "material", "pipeline_version", "attempt"}
        )
        self.assertEqual(message["tenant_id"], TENANT)
        self.assertEqual(message["blob"], f"wsi-publico/{SLIDE}.svs")
        self.assertEqual((message["organ"], message["material"], message["attempt"]), ("estomago", "biopsia", 0))
        self.assertIn(message["job_id"], out)
        self.assertNotIn(TOKEN, out)

    def test_slide_without_organ_goes_as_null(self):
        calls = Calls(psql_out=f"{TENANT}|{SLIDE}.svs||citologia\n")
        run_main(calls, "job", "--tenant", "publico", "--lamina", SLIDE)
        message = json.loads(ElementTree.fromstring(calls.log[2][2]).findtext("MessageText"))
        self.assertIsNone(message["organ"])

    def test_failed_send_names_the_job_and_fails(self):
        calls = Calls(psql_out=f"{TENANT}|{SLIDE}.svs|estomago|biopsia\n", fail_send=True)
        code, _, err = run_main(calls, "job", "--tenant", "publico", "--lamina", SLIDE)
        self.assertEqual(code, 1)
        self.assertIn("FALHA", err)
        self.assertNotIn(TOKEN, err)


class ExistingJob(unittest.TestCase):
    """reenviar and forjar: both read a job of the tenant and send its message."""

    def test_reads_the_job_in_the_database_first_and_writes_nothing(self):
        for command in ("reenviar", "forjar"):
            calls = Calls(psql_out=STORED)
            with self.subTest(command=command):
                code, out, _ = run_main(calls, command, "--tenant", "publico", "--job", JOB)
                self.assertEqual(code, 0)
                self.assertEqual([kind for kind, *_ in calls.log], ["psql", "imds", "fila"])
                _, args, sql = calls.log[0]
                self.assertEqual(args[:6], ["docker", "exec", "-i", "-u", "postgres", "pathsol-banco"])
                self.assertIn(f"job={JOB}", args)
                self.assertIn("SET LOCAL ROLE pathsol_produtor", sql)
                self.assertNotRegex(sql, r"INSERT|UPDATE|DELETE")
                self.assertIn(JOB, out)
                self.assertNotIn(TOKEN, out)

    def test_failed_send_names_the_job_and_fails(self):
        for command in ("reenviar", "forjar"):
            calls = Calls(psql_out=STORED, fail_send=True)
            with self.subTest(command=command):
                code, _, err = run_main(calls, command, "--tenant", "publico", "--job", JOB)
                self.assertEqual(code, 1)
                self.assertIn("FALHA", err)
                self.assertIn(JOB, err)
                self.assertNotIn(TOKEN, err)

    def test_refuses_a_job_that_is_not_a_uuid_before_any_call(self):
        for command in ("reenviar", "forjar"):
            for value in ("caso-12345", JOB.upper(), ""):
                calls = Calls(psql_out=STORED)
                with self.subTest(command=command, value=value):
                    code, _, _ = run_main(calls, command, "--tenant", "publico", "--job", value)
                    self.assertNotEqual(code, 0)
                    self.assertEqual(calls.log, [])


class Resend(unittest.TestCase):
    def test_sends_the_text_that_job_sent(self):
        first = Calls(psql_out=f"{TENANT}|{SLIDE}.svs|estomago|biopsia\n")
        self.assertEqual(run_main(first, "job", "--tenant", "publico", "--lamina", SLIDE)[0], 0)
        again = Calls(psql_out=STORED)
        code, _, _ = run_main(again, "reenviar", "--tenant", "publico", "--job", json.loads(sent_text(first))["job_id"])
        self.assertEqual(code, 0)
        self.assertEqual(sent_text(again), sent_text(first))


class Forge(unittest.TestCase):
    def test_changes_only_the_tenant_to_a_fresh_uuid_that_it_prints(self):
        expected = {"job_id": JOB, "slide_id": SLIDE, "blob": f"wsi-publico/{SLIDE}.svs", "organ": "estomago",
                    "material": "biopsia", "pipeline_version": "fase4-teste", "attempt": 0}
        tenants = []
        for _ in range(2):
            calls = Calls(psql_out=STORED)
            code, out, _ = run_main(calls, "forjar", "--tenant", "publico", "--job", JOB)
            self.assertEqual(code, 0)
            message = json.loads(sent_text(calls))
            tenant = message.pop("tenant_id")
            self.assertNotEqual(tenant, TENANT)
            self.assertEqual(message, expected)
            self.assertEqual(str(uuid.UUID(tenant)), tenant)
            self.assertIn(tenant, out)
            tenants.append(tenant)
        self.assertNotEqual(tenants[0], tenants[1])


class Slide(unittest.TestCase):
    def test_inserts_the_slide_as_the_producer(self):
        calls = Calls()
        code, _, _ = run_main(
            calls, "lamina", "--tenant", "publico", "--arquivo", f"{SLIDE}.svs", "--sha256", SHA,
            "--material", "biopsia", "--coloracao", "HE", "--orgao", "estomago",
        )
        self.assertEqual(code, 0)
        _, args, sql = calls.log[0]
        self.assertIn("SET LOCAL ROLE pathsol_produtor", sql)
        self.assertIn("INSERT INTO slides", sql)
        self.assertIn(f"slide={SLIDE}", args)
        self.assertIn(f"nome={SLIDE}.svs", args)

    def test_refuses_bad_values_before_any_call(self):
        bad = (
            ("--arquivo", "caso-12345.svs"),
            ("--arquivo", f"{SLIDE}"),
            ("--sha256", "abc"),
            ("--material", "congelacao"),
            ("--coloracao", "h&e; drop"),
            ("--tenant", "Publico"),
        )
        for flag, value in bad:
            args = {"--tenant": "publico", "--arquivo": f"{SLIDE}.svs", "--sha256": SHA, "--material": "biopsia", "--coloracao": "HE"}
            args[flag] = value
            calls = Calls()
            with self.subTest(flag=flag, value=value):
                code, _, _ = run_main(calls, "lamina", *[x for pair in args.items() for x in pair])
                self.assertNotEqual(code, 0)
                self.assertEqual(calls.log, [])


class Tenant(unittest.TestCase):
    def test_creates_the_tenant_once_and_prints_its_id(self):
        calls = Calls(psql_out=f"{TENANT}\n")
        code, out, _ = run_main(calls, "tenant", "publico")
        self.assertEqual(code, 0)
        _, args, sql = calls.log[0]
        self.assertIn("ON CONFLICT (slug) DO NOTHING", sql)
        self.assertNotIn("SET LOCAL ROLE", sql)
        self.assertIn(TENANT, out)


if __name__ == "__main__":
    unittest.main()
