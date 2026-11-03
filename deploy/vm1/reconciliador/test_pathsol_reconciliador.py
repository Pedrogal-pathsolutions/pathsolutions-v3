import datetime
import io
import json
import os
import subprocess
import syslog
import tempfile
import unittest
import urllib.error
from unittest import mock
from xml.sax.saxutils import escape

import pathsol_reconciliador as reconciliador

UTC = datetime.timezone.utc
VM2 = (
    "https://management.azure.com/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1"
    "/resourceGroups/rg-prod-brsouth-001/providers/Microsoft.Compute/virtualMachines/vm-appfoundation-prod-001"
)
INSTANCE_VIEW = f"{VM2}/instanceView?api-version=2025-04-01"
START = f"{VM2}/start?api-version=2025-04-01"
DEALLOCATE = f"{VM2}/deallocate?api-version=2025-04-01"
PEEK = "https://pathsolwsiv3.queue.core.windows.net/jobs/messages?peekonly=true&numofmessages=1"
IMDS = "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource="
IMDS_ARM = IMDS + "https://management.azure.com/"
IMDS_STORAGE = IMDS + "https://storage.azure.com/"
TOKENS = {IMDS_ARM: "eyJhcm0tdm0xIn0", IMDS_STORAGE: "eyJmaWxhLXZtMSJ9"}
HEARTBEAT_QUERY = [
    "docker", "exec", "-u", "postgres", "pathsol-banco", "psql", "-X", "-At", "-d", "pathsol",
    "-c", "select extract(epoch from now() - max(beat_at))::bigint from worker_heartbeat",
]
# A message as the producer writes it, with synthetic identifiers only.
JOB_ID = "6b0f3c9e-2d4a-4f1b-9c7e-1a2b3c4d5e6f"
TENANT_ID = "0e7d1c2b-3a4f-4b5c-8d9e-0f1a2b3c4d5e"
SLIDE_ID = "9a8b7c6d-5e4f-4a3b-8c2d-1e0f9a8b7c6d"
MESSAGE_TEXT = json.dumps({
    "job_id": JOB_ID, "tenant_id": TENANT_ID, "slide_id": SLIDE_ID, "blob": f"wsi-publico/{SLIDE_ID}.svs",
    "organ": None, "material": "peca", "pipeline_version": "fase4-teste", "attempt": 0,
})
NEVER_LOGGED = (*TOKENS.values(), JOB_ID, TENANT_ID, SLIDE_ID, "wsi-publico", "fase4-teste")

NOW = datetime.datetime(2026, 11, 3, 15, 0, tzinfo=UTC)  # 12:00 in Brasilia
JOB = "Tue, 03 Nov 2026 14:45:00 GMT"  # 900 s before NOW
STARTED = "2026-11-03T14:29:59.1234567+00:00"  # ARM's format; 1800.88 s before NOW
ENV = {"PATHSOL_VISIBILIDADE": "1800", "PATHSOL_PIOR_JOB": "900", "PATHSOL_ESPERA_PARTIDA": "900", "PATHSOL_DESLIGA_VM1": "02:00"}


def utc(*fields):
    return datetime.datetime(*fields, tzinfo=UTC)


def http_error(url, code, reason):
    return urllib.error.HTTPError(url, code, reason, {}, None)


class Response(io.BytesIO):
    def __init__(self, body=b"", status=200):
        super().__init__(body)
        self.status = status


class Azure:
    """Fake IMDS, queue and ARM over one state of the queue and of VM2. Keeps
    (method, url) of every call past the IMDS; a wrong token, header or call
    gets the error the service would give."""

    def __init__(self, inserted=None, power="deallocated", since=STARTED, provisioning="succeeded", failing=()):
        self.inserted, self.power, self.since, self.provisioning = inserted, power, since, provisioning
        self.failing = failing
        self.calls = []

    def __call__(self, request, timeout=None):
        url, method = request.full_url, request.get_method()
        if url in TOKENS:
            if url in self.failing or request.get_header("Metadata") != "true":
                raise http_error(url, 400, "Bad Request")
            resource = url.split("resource=", 1)[1]
            return Response(json.dumps({"access_token": TOKENS[url], "expires_on": "1793800000",
                                        "resource": resource, "token_type": "Bearer"}).encode())
        self.calls.append((method, url))
        if url in self.failing:
            raise http_error(url, 409, "Conflict")
        if (method, url) == ("GET", PEEK):
            self.authorize(request, IMDS_STORAGE)
            if request.get_header("X-ms-version") != "2024-11-04" or not request.get_header("X-ms-date"):
                raise http_error(url, 400, "Bad Request")
            return Response(self.peek_answer())
        if (method, url) == ("GET", INSTANCE_VIEW):
            self.authorize(request, IMDS_ARM)
            return Response(json.dumps(self.instance_view()).encode())
        if method == "POST" and url in (START, DEALLOCATE) and not request.data:
            self.authorize(request, IMDS_ARM)
            return Response(status=202)
        raise http_error(url, 404, "Not Found")

    @staticmethod
    def authorize(request, imds_url):
        if request.get_header("Authorization") != f"Bearer {TOKENS[imds_url]}":
            raise http_error(request.full_url, 401, "Unauthorized")

    def peek_answer(self):
        if self.inserted is None:
            return b'<?xml version="1.0" encoding="utf-8"?><QueueMessagesList />'
        return (
            '<?xml version="1.0" encoding="utf-8"?><QueueMessagesList><QueueMessage>'
            "<MessageId>0b1e6a5c-8f43-4d7e-a6c2-6c1f4d3e9b20</MessageId>"
            f"<InsertionTime>{self.inserted}</InsertionTime>"
            "<ExpirationTime>Fri, 31 Dec 9999 23:59:59 GMT</ExpirationTime>"
            "<DequeueCount>0</DequeueCount>"
            f"<MessageText>{escape(MESSAGE_TEXT)}</MessageText>"
            "</QueueMessage></QueueMessagesList>"
        ).encode()

    def instance_view(self):
        provisioning = {"code": f"ProvisioningState/{self.provisioning}", "level": "Info",
                        "displayStatus": f"Provisioning {self.provisioning}"}
        if self.since:
            provisioning["time"] = self.since
        power = {"code": f"PowerState/{self.power}", "level": "Info", "displayStatus": f"VM {self.power}"}
        return {"hyperVGeneration": "V2", "statuses": [provisioning, power]}

    def posts(self):
        return [url for method, url in self.calls if method == "POST"]


class Database:
    """Fake docker exec of psql: the heartbeat age as psql -At prints it."""

    def __init__(self, out="1801\n", error=None):
        self.out, self.error = out, error
        self.calls = []

    def __call__(self, args):
        self.calls.append(args)
        if self.error:
            raise self.error
        return subprocess.CompletedProcess(args, 0, stdout=self.out, stderr="")


def failures(lines):
    return [text for priority, text in lines if priority == syslog.LOG_ERR]


class ReconcilerTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.marker = os.path.join(directory.name, "manutencao-vm2")

    def write_marker(self, text, written):
        with open(self.marker, "w", encoding="utf-8") as file:
            file.write(text)
        os.utime(self.marker, (written.timestamp(), written.timestamp()))

    def reconcile(self, azure, database=None, now=NOW, env=ENV, uptime=36000.0):
        """One pass; returns its result and the syslog lines as (priority, text)."""
        lines = []
        with mock.patch.object(reconciliador.syslog, "syslog", lambda priority, text: lines.append((priority, text))):
            ok = reconciliador.reconcile(now, uptime, env, self.marker, azure, database or Database())
        for priority, text in lines:
            self.assertIn((priority, text.split(" ", 1)[0]), {(syslog.LOG_INFO, "OK"), (syslog.LOG_ERR, "FALHA")}, text)
            for value in NEVER_LOGGED:
                self.assertNotIn(value, text)
        return ok, lines


class Start(ReconcilerTest):
    def test_starts_deallocated_vm2_once_the_oldest_job_waited_enough(self):
        azure = Azure(inserted=JOB)
        ok, lines = self.reconcile(azure)
        self.assertTrue(ok)
        self.assertEqual(azure.calls, [("GET", PEEK), ("GET", INSTANCE_VIEW), ("POST", START)])
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], (syslog.LOG_INFO, "OK idade do job mais antigo: 900 s"))
        self.assertEqual(failures(lines), [])

    def test_starts_stopped_vm2(self):
        azure = Azure(inserted=JOB, power="stopped")
        ok, _ = self.reconcile(azure)
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [START])

    def test_never_starts_running_or_changing_vm2(self):
        for power in ("starting", "running", "stopping", "deallocating"):
            with self.subTest(power=power):
                azure = Azure(inserted=JOB, power=power)
                ok, lines = self.reconcile(azure)
                self.assertTrue(ok)
                self.assertEqual(azure.posts(), [])
                self.assertEqual(lines, [(syslog.LOG_INFO, "OK idade do job mais antigo: 900 s")])

    def test_waits_until_the_oldest_job_waited_enough(self):
        azure = Azure(inserted=JOB)
        ok, lines = self.reconcile(azure, now=utc(2026, 11, 3, 14, 59, 59))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])
        self.assertEqual(lines, [(syslog.LOG_INFO, "OK idade do job mais antigo: 899 s")])

    def test_construction_starts_on_the_first_job(self):
        azure = Azure(inserted="Tue, 03 Nov 2026 15:00:00 GMT")
        ok, _ = self.reconcile(azure, env={**ENV, "PATHSOL_ESPERA_PARTIDA": "0"})
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [START])


class ShutdownRule(ReconcilerTest):
    """VM1 shuts down at 02:00 UTC; the job came at 01:00."""

    JOB = "Wed, 04 Nov 2026 01:00:00 GMT"

    def test_starts_when_vm2_would_be_ready_and_done_before_vm1_shuts_down(self):
        # 01:39:59 + 300 s until the worker is ready + 900 s of the worst job = 01:59:59
        azure = Azure(inserted=self.JOB)
        ok, _ = self.reconcile(azure, now=utc(2026, 11, 4, 1, 39, 59))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [START])

    def test_holds_a_start_that_would_reach_the_shutdown_and_says_so_once(self):
        azure = Azure(inserted=self.JOB)
        ok, lines = self.reconcile(azure, now=utc(2026, 11, 4, 1, 40))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], (syslog.LOG_INFO, "OK idade do job mais antigo: 2400 s"))
        self.assertEqual(lines[1][0], syslog.LOG_INFO)
        self.assertIn("2026-11-04T02:00:00Z", lines[1][1])

    def test_worst_job_and_shutdown_time_come_from_the_unit(self):
        azure = Azure(inserted=self.JOB)
        self.reconcile(azure, now=utc(2026, 11, 4, 1, 39, 59), env={**ENV, "PATHSOL_PIOR_JOB": "901"})
        self.assertEqual(azure.posts(), [])
        azure = Azure(inserted=self.JOB)
        self.reconcile(azure, now=utc(2026, 11, 4, 1, 40), env={**ENV, "PATHSOL_DESLIGA_VM1": "03:00"})
        self.assertEqual(azure.posts(), [START])

    def test_no_start_while_the_shutdown_is_under_way(self):
        # On 30/10 the platform reached VM1's guest at 02:02:03.
        azure = Azure(inserted=self.JOB)
        ok, lines = self.reconcile(azure, now=utc(2026, 11, 4, 2, 2, 3))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])
        self.assertEqual(len(lines), 2)
        self.assertIn("2026-11-04T02:00:00Z", lines[1][1])

    def test_vm1_still_on_well_after_its_shutdown_starts_vm2(self):
        azure = Azure(inserted=self.JOB)
        self.reconcile(azure, now=utc(2026, 11, 4, 2, 10))
        self.assertEqual(azure.posts(), [START])


class NextShutdown(unittest.TestCase):
    def test_around_midnight_utc(self):
        cases = (
            (utc(2026, 11, 3, 15, 0), utc(2026, 11, 4, 2, 0)),
            (utc(2026, 11, 3, 23, 59, 59), utc(2026, 11, 4, 2, 0)),
            (utc(2026, 11, 4, 0, 0, 1), utc(2026, 11, 4, 2, 0)),
            (utc(2026, 11, 4, 1, 59, 59), utc(2026, 11, 4, 2, 0)),
            (utc(2026, 11, 4, 2, 9, 59), utc(2026, 11, 4, 2, 0)),  # still under way
            (utc(2026, 11, 4, 2, 10), utc(2026, 11, 5, 2, 0)),
        )
        for now, expected in cases:
            with self.subTest(now=now):
                self.assertEqual(reconciliador.next_shutdown(now, datetime.time(2, 0)), expected)

    def test_shutdown_just_before_midnight_is_still_under_way_after_it(self):
        at = datetime.time(23, 55)
        self.assertEqual(reconciliador.next_shutdown(utc(2026, 11, 3, 23, 50), at), utc(2026, 11, 3, 23, 55))
        self.assertEqual(reconciliador.next_shutdown(utc(2026, 11, 4, 0, 4, 59), at), utc(2026, 11, 3, 23, 55))
        self.assertEqual(reconciliador.next_shutdown(utc(2026, 11, 4, 0, 5), at), utc(2026, 11, 4, 23, 55))


class ArmTime(unittest.TestCase):
    def test_iso_8601_as_arm_writes_it_on_python_3_10(self):
        cases = (
            ("2026-11-03T14:29:59.1234567+00:00", utc(2026, 11, 3, 14, 29, 59, 123456)),
            ("2026-11-03T14:29:59Z", utc(2026, 11, 3, 14, 29, 59)),
            ("2026-11-03T11:29:59.5-03:00", utc(2026, 11, 3, 14, 29, 59, 500000)),
        )
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(reconciliador.arm_time(text), expected)

    def test_anything_else_is_refused(self):
        for text in ("2026-11-03 14:29:59", "2026-11-03T14:29:59", "ontem"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                reconciliador.arm_time(text)


class Deallocate(ReconcilerTest):
    def test_deallocates_running_vm2_with_no_job_and_a_stale_heartbeat(self):
        azure, database = Azure(power="running"), Database("1801\n")
        ok, lines = self.reconcile(azure, database)
        self.assertTrue(ok)
        self.assertEqual(azure.calls, [("GET", PEEK), ("GET", INSTANCE_VIEW), ("POST", DEALLOCATE)])
        self.assertEqual(database.calls, [HEARTBEAT_QUERY])
        self.assertEqual(len(lines), 1)
        self.assertEqual(failures(lines), [])

    def test_worker_that_never_beat_counts_as_stale(self):
        azure = Azure(power="running")
        ok, _ = self.reconcile(azure, Database("\n"))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [DEALLOCATE])

    def test_visible_job_keeps_vm2_even_without_heartbeat(self):
        azure = Azure(inserted=JOB, power="running")
        ok, _ = self.reconcile(azure, Database("\n"))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])

    def test_recent_start_keeps_vm2(self):
        azure = Azure(power="running", since="2026-11-03T14:30:00.0000000+00:00")  # exactly 1800 s
        ok, lines = self.reconcile(azure, Database("\n"))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])
        self.assertEqual(lines, [])

    def test_recent_heartbeat_keeps_vm2(self):
        azure = Azure(power="running")
        ok, lines = self.reconcile(azure, Database("1800\n"))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])
        self.assertEqual(lines, [])

    def test_visibility_timeout_comes_from_the_unit(self):
        env = {**ENV, "PATHSOL_VISIBILIDADE": "3600"}
        started = "2026-11-03T13:59:59.0000000+00:00"  # 3601 s
        azure = Azure(power="running", since=STARTED)
        self.reconcile(azure, Database("3601\n"), env=env)
        self.assertEqual(azure.posts(), [])
        azure = Azure(power="running", since=started)
        self.reconcile(azure, Database("3000\n"), env=env)
        self.assertEqual(azure.posts(), [])
        azure = Azure(power="running", since=started)
        self.reconcile(azure, Database("3601\n"), env=env)
        self.assertEqual(azure.posts(), [DEALLOCATE])

    def test_failed_heartbeat_query_skips_the_rule(self):
        stderr = 'ERROR:  relation "worker_heartbeat" does not exist\nLINE 1: ...from worker_heartbeat\n      ^\n'
        azure = Azure(power="running")
        ok, lines = self.reconcile(azure, Database(error=subprocess.CalledProcessError(1, HEARTBEAT_QUERY, "", stderr)))
        self.assertFalse(ok)
        self.assertEqual(azure.posts(), [])
        [failure] = failures(lines)
        self.assertIn('relation "worker_heartbeat" does not exist', failure)

    def test_running_vm2_under_another_operation_waits(self):
        azure = Azure(power="running", provisioning="updating", since=None)
        ok, lines = self.reconcile(azure, Database("\n"))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])
        self.assertEqual(lines, [])

    def test_stopped_vm2_keeps_billing_and_is_deallocated(self):
        azure = Azure(power="stopped")
        ok, lines = self.reconcile(azure, Database("\n"))
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [DEALLOCATE])
        self.assertEqual(failures(lines), [])

    def test_only_running_or_stopped_vm2_is_deallocated_and_an_idle_pass_is_silent(self):
        for power in ("deallocated", "starting", "stopping", "deallocating"):
            with self.subTest(power=power):
                azure = Azure(power=power)
                ok, lines = self.reconcile(azure, Database("\n"))
                self.assertTrue(ok)
                self.assertEqual(azure.posts(), [])
                self.assertEqual(lines, [])


class Maintenance(ReconcilerTest):
    def test_valid_marker_holds_start_and_deallocate(self):
        self.write_marker("2026-11-03T16:00:00Z\n", written=utc(2026, 11, 3, 14, 30))
        for azure in (Azure(inserted=JOB), Azure(power="running")):
            with self.subTest(power=azure.power):
                ok, lines = self.reconcile(azure, Database("\n"))
                self.assertTrue(ok)
                self.assertEqual(azure.posts(), [])
                self.assertEqual(lines[:1], [(syslog.LOG_INFO, "OK manutenção até 2026-11-03T16:00:00Z")])

    def test_job_age_is_still_logged(self):
        self.write_marker("2026-11-03T16:00:00Z\n", written=utc(2026, 11, 3, 14, 30))
        ok, lines = self.reconcile(Azure(inserted=JOB))
        self.assertTrue(ok)
        self.assertEqual(lines, [
            (syslog.LOG_INFO, "OK manutenção até 2026-11-03T16:00:00Z"),
            (syslog.LOG_INFO, "OK idade do job mais antigo: 900 s"),
        ])

    def test_maintenance_is_logged_even_when_the_queue_fails(self):
        self.write_marker("2026-11-03T16:00:00Z\n", written=utc(2026, 11, 3, 14, 30))
        ok, lines = self.reconcile(Azure(inserted=JOB, failing={PEEK}))
        self.assertFalse(ok)
        self.assertEqual(lines[0], (syslog.LOG_INFO, "OK manutenção até 2026-11-03T16:00:00Z"))
        self.assertEqual(len(failures(lines)), 1)

    def test_marker_may_end_four_hours_after_it_was_written(self):
        self.write_marker("2026-11-03T18:00:00Z", written=utc(2026, 11, 3, 14, 0))
        azure = Azure(inserted=JOB)
        ok, _ = self.reconcile(azure)
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [])

    def assert_ignored(self):
        """The marker is logged as FALHA once and the start goes ahead."""
        azure = Azure(inserted=JOB)
        ok, lines = self.reconcile(azure)
        self.assertFalse(ok)
        self.assertEqual(azure.posts(), [START])
        self.assertEqual(len(failures(lines)), 1)
        return failures(lines)[0]

    def test_marker_beyond_four_hours_is_ignored(self):
        self.write_marker("2026-11-03T18:00:01Z\n", written=utc(2026, 11, 3, 14, 0))
        self.assertIn("2026-11-03T18:00:01Z", self.assert_ignored())

    def test_expired_marker_is_ignored(self):
        for deadline in ("2026-11-03T15:00:00Z", "2026-11-03T14:59:59Z"):
            with self.subTest(deadline=deadline):
                self.write_marker(deadline + "\n", written=utc(2026, 11, 3, 14, 0))
                self.assertIn(deadline, self.assert_ignored())

    def test_malformed_marker_is_ignored(self):
        texts = ("", "amanhã cedo\n", "2026-11-03T16:00:00\n", "2026-11-03T16:00:00+00:00\n", " 2026-11-03T16:00:00Z\n",
                 "2026-11-03T16:00:00Z\n2026-11-03T17:00:00Z\n", "2026-11-31T16:00:00Z\n")
        for text in texts:
            with self.subTest(text=text):
                self.write_marker(text, written=utc(2026, 11, 3, 14, 0))
                self.assertNotIn("amanhã", self.assert_ignored())

    def test_unreadable_marker_is_ignored(self):
        os.mkdir(self.marker)
        self.assert_ignored()

    def test_missing_marker_is_silent(self):
        azure = Azure(inserted=JOB)
        ok, lines = self.reconcile(azure)
        self.assertTrue(ok)
        self.assertEqual(azure.posts(), [START])
        self.assertEqual(failures(lines), [])


class JobAge(ReconcilerTest):
    def test_counts_only_the_time_vm1_has_been_on(self):
        # Sent at 22:50 in Brasilia; VM1 came back at 06:00, 10 min ago.
        azure = Azure(inserted="Tue, 03 Nov 2026 01:50:00 GMT")
        ok, lines = self.reconcile(azure, now=utc(2026, 11, 3, 9, 10), uptime=600.0)
        self.assertTrue(ok)
        self.assertEqual(lines[:1], [(syslog.LOG_INFO, "OK idade do job mais antigo: 600 s")])
        self.assertEqual(azure.posts(), [START])  # it waited all night: no extra wait

    def test_message_text_never_reaches_the_log(self):
        for azure in (Azure(inserted=JOB), Azure(inserted=JOB, power="running"), Azure(inserted=JOB, failing={START})):
            with self.subTest(power=azure.power, failing=azure.failing):
                _, lines = self.reconcile(azure)
                self.assertTrue(lines)
                logged = "\n".join(text for _, text in lines)
                self.assertNotIn(MESSAGE_TEXT, logged)
                self.assertNotIn(JOB_ID, logged)


class Failures(ReconcilerTest):
    def test_failed_queue_call_decides_nothing(self):
        azure = Azure(inserted=JOB, failing={PEEK})
        ok, lines = self.reconcile(azure)
        self.assertFalse(ok)
        self.assertEqual(azure.calls, [("GET", PEEK)])
        [failure] = failures(lines)
        self.assertIn("409", failure)

    def test_unexpected_queue_answer_decides_nothing(self):
        azure = Azure(inserted="ontem")
        ok, lines = self.reconcile(azure)
        self.assertFalse(ok)
        self.assertEqual(azure.calls, [("GET", PEEK)])
        self.assertEqual(len(failures(lines)), 1)

    def test_failed_token_decides_nothing(self):
        for imds in (IMDS_STORAGE, IMDS_ARM):
            with self.subTest(imds=imds):
                azure = Azure(inserted=JOB, failing={imds})
                ok, lines = self.reconcile(azure)
                self.assertFalse(ok)
                self.assertEqual(azure.posts(), [])
                self.assertEqual(len(failures(lines)), 1)

    def test_failed_instance_view_decides_nothing(self):
        azure = Azure(inserted=JOB, failing={INSTANCE_VIEW})
        ok, lines = self.reconcile(azure)
        self.assertFalse(ok)
        self.assertEqual(azure.posts(), [])
        [failure] = failures(lines)
        self.assertIn("409", failure)

    def test_failed_start_is_a_failure(self):
        azure = Azure(inserted=JOB, failing={START})
        ok, lines = self.reconcile(azure)
        self.assertFalse(ok)
        self.assertEqual(azure.posts(), [START])
        self.assertEqual([priority for priority, _ in lines], [syslog.LOG_INFO, syslog.LOG_ERR])

    def test_failed_deallocate_is_a_failure(self):
        azure = Azure(power="running", failing={DEALLOCATE})
        ok, lines = self.reconcile(azure, Database("\n"))
        self.assertFalse(ok)
        self.assertEqual(azure.posts(), [DEALLOCATE])
        self.assertEqual([priority for priority, _ in lines], [syslog.LOG_ERR])

    def test_invalid_unit_value_decides_nothing(self):
        azure = Azure(inserted=JOB)
        ok, lines = self.reconcile(azure, env={**ENV, "PATHSOL_PIOR_JOB": "15 min"})
        self.assertFalse(ok)
        self.assertEqual(azure.calls, [])
        self.assertEqual(len(failures(lines)), 1)


class Main(unittest.TestCase):
    def test_exit_code_follows_the_pass_and_lines_go_to_local0(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        for azure, code, priorities in ((Azure(), 0, []), (Azure(failing={PEEK}), 1, [syslog.LOG_ERR])):
            opened, logged = [], []
            with mock.patch.object(reconciliador, "urlopen", azure), \
                    mock.patch.object(reconciliador, "run", Database()), \
                    mock.patch.object(reconciliador, "MARKER", os.path.join(directory.name, "manutencao-vm2")), \
                    mock.patch.object(reconciliador.syslog, "openlog",
                                      lambda ident, logoption=0, facility=0: opened.append((ident, facility))), \
                    mock.patch.object(reconciliador.syslog, "syslog", lambda priority, text: logged.append(priority)):
                with self.assertRaises(SystemExit) as exit_:
                    reconciliador.main()
            with self.subTest(code=code):
                self.assertEqual(exit_.exception.code, code)
                self.assertEqual(opened, [("pathsol-reconciliador", syslog.LOG_LOCAL0)])
                self.assertEqual(logged, priorities)


if __name__ == "__main__":
    unittest.main()
