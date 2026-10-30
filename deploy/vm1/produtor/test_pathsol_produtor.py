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
SHA = "a" * 64
TOKEN = "eyJ0b2tlbi1kYS12bTEifQ"


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
