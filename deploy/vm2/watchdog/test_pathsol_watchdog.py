import io
import json
import os
import subprocess
import syslog
import tempfile
import unittest
import urllib.error
from unittest import mock

import pathsol_watchdog as watchdog

NOW = 1_793_707_200.0  # 2026-11-03T12:00:00Z
TOKEN = "eyJ0b2tlbi1kYS12bTIifQ"
IMDS = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://management.azure.com/"
)
DEALLOCATE = (
    "https://management.azure.com/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1"
    "/resourceGroups/rg-prod-brsouth-001/providers/Microsoft.Compute/virtualMachines"
    "/vm-appfoundation-prod-001/deallocate?api-version=2025-04-01"
)
GPU_CHECK = ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]
TOKEN_ANSWER = {
    "access_token": TOKEN,
    "client_id": "00000000-0000-0000-0000-0000000000a2",
    "expires_in": "86399",
    "expires_on": "1793793599",
    "ext_expires_in": "86399",
    "not_before": "1793706900",
    "resource": "https://management.azure.com/",
    "token_type": "Bearer",
}
OTHER_SPAWNS = ("system", "execv", "execve", "fork", "posix_spawn", "posix_spawnp")


def http_error(url, code, body):
    return urllib.error.HTTPError(url, code, "erro", {}, io.BytesIO(json.dumps(body).encode()))


class Syslog:
    """Fake syslog module: keeps the lines instead of sending them."""

    LOG_INFO, LOG_ERR, LOG_LOCAL0 = syslog.LOG_INFO, syslog.LOG_ERR, syslog.LOG_LOCAL0

    def __init__(self):
        self.lines, self.opened = [], None

    def openlog(self, ident, logoption, facility):
        self.opened = (ident, facility)

    def syslog(self, priority, message):
        self.lines.append((priority, message))


class Response(io.BytesIO):
    def __init__(self, body=b"", status=200):
        super().__init__(body)
        self.status = status


class Azure:
    """Fake IMDS and ARM: keeps every request with its timeout. ARM answers
    arm_answer, a status or an exception to raise."""

    def __init__(self):
        self.imds_error, self.arm_answer, self.requests = None, 202, []

    def __call__(self, request, timeout=None):
        self.requests.append((request, timeout))
        if request.full_url.startswith("http://169.254.169.254/"):
            if self.imds_error:
                raise self.imds_error
            return Response(json.dumps(TOKEN_ANSWER).encode())
        if isinstance(self.arm_answer, Exception):
            raise self.arm_answer
        return Response(status=self.arm_answer)

    def arm(self):
        return [request for request, _ in self.requests if not request.full_url.startswith("http://169.254.169.254/")]


class Gpu:
    """Fake subprocess.Popen, answering like nvidia-smi on a T4. As the real
    one, it writes bytes, which come out only through pipes and are decoded
    only in text mode, strictly unless told otherwise. hangs: no answer, like
    a process stuck in the driver, which SIGKILL does not end; missing: no
    binary."""

    def __init__(self):
        self.out, self.err, self.code = b"Tesla T4\n", b"", 0
        self.hangs = self.missing = False
        self.started, self.timeout, self.killed, self.waited = [], None, False, False

    def __call__(self, args, stdout=None, stderr=None, text=None, encoding=None, errors=None, **kwargs):
        self.started.append(list(args))
        if self.missing:
            raise FileNotFoundError(2, "No such file or directory", args[0])
        self.pipes = (stdout == subprocess.PIPE, stderr == subprocess.PIPE)
        self.text = bool(text or encoding or errors or kwargs.get("universal_newlines"))
        self.decoding = (encoding or "utf-8", errors or "strict")
        self.returncode = None
        return self

    def communicate(self, input=None, timeout=None):
        self.timeout = timeout
        if self.hangs:
            if timeout is None:
                raise AssertionError("communicate() sem prazo nunca volta")
            raise subprocess.TimeoutExpired(self.started[-1], timeout)
        self.returncode = self.code
        out, err = (value.decode(*self.decoding) if self.text else value for value in (self.out, self.err))
        return (out if self.pipes[0] else None), (err if self.pipes[1] else None)

    def kill(self):
        self.killed = True

    def wait(self, timeout=None):
        self.waited = True
        return self.returncode


class Pass(unittest.TestCase):
    """One pass of the watchdog with fake IMDS, ARM, nvidia-smi and syslog,
    real files in a scratch directory, and NOW and the uptime passed in.

    After every test: no program was started but nvidia-smi, by subprocess or
    by os, and ARM was asked for nothing but deallocate. VM2 is never stopped
    from inside (shutdown, poweroff, ARM powerOff), which keeps billing.
    """

    def setUp(self):
        scratch = tempfile.TemporaryDirectory()
        self.addCleanup(scratch.cleanup)
        self.marker = os.path.join(scratch.name, "manutencao")
        self.pulse = os.path.join(scratch.name, "pulso")
        self.uptime_file = os.path.join(scratch.name, "uptime")
        self.syslog, self.azure, self.gpu, self.spawned = Syslog(), Azure(), Gpu(), []
        patches = [
            mock.patch.object(watchdog, "MARKER", self.marker),
            mock.patch.object(watchdog, "PULSE", self.pulse),
            mock.patch.object(watchdog, "UPTIME", self.uptime_file),
            mock.patch.object(watchdog, "syslog", self.syslog),
            mock.patch.object(watchdog, "urlopen", self.azure),
            mock.patch.object(subprocess, "Popen", self.gpu),
        ]
        patches += [mock.patch.object(os, name, self.recorder(name)) for name in OTHER_SPAWNS]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def recorder(self, name):
        def record(*args, **kwargs):
            self.spawned.append((name, args))
            return 0
        return record

    def tearDown(self):
        self.assertEqual(self.spawned, [])
        for args in self.gpu.started:
            self.assertEqual(args, GPU_CHECK)
        for request in self.azure.arm():
            self.assertEqual((request.get_method(), request.full_url), ("POST", DEALLOCATE))

    def watch(self, uptime):
        return watchdog.watch(NOW, uptime)

    def beat(self, age):
        """The worker touched the pulse file `age` seconds before NOW."""
        with open(self.pulse, "w"):
            pass
        os.utime(self.pulse, (NOW - age, NOW - age))

    def mark(self, text, written=NOW - 600):
        """The operator wrote the maintenance marker, 10 min before NOW unless said."""
        with open(self.marker, "w", encoding="utf-8") as file:
            file.write(text)
        os.utime(self.marker, (written, written))

    def assert_nothing_done(self):
        self.assertEqual(self.azure.requests, [])
        self.assertEqual(self.syslog.lines, [])

    def assert_deallocated(self, reason):
        """One deallocation, accepted, logged once at info with its reason and ARM's status."""
        self.assertEqual(len(self.azure.arm()), 1)
        [(priority, message)] = self.syslog.lines
        self.assertEqual(priority, syslog.LOG_INFO)
        self.assertTrue(message.startswith("OK "), message)
        self.assertIn(reason, message)
        self.assertIn("202", message)
        return message


class Start(Pass):
    def test_first_5_min_are_left_alone(self):
        # No heartbeat and a failing GPU, still during boot and model load.
        self.gpu.code = 9
        self.assertTrue(self.watch(299))
        self.assertEqual(self.gpu.started, [])
        self.assert_nothing_done()

    def test_gpu_that_answers_from_5_min_is_silent(self):
        self.assertTrue(self.watch(300))
        self.assertEqual(self.gpu.started, [GPU_CHECK])
        self.assertEqual(self.gpu.timeout, 60)
        self.assert_nothing_done()

    def test_heartbeat_is_not_checked_before_15_min(self):
        # No pulse file at all: only the GPU counts at 899 s.
        self.assertTrue(self.watch(899))
        self.assertEqual(self.gpu.started, [GPU_CHECK])
        self.assert_nothing_done()

    def test_nvidia_smi_exiting_with_an_error_deallocates(self):
        self.gpu.code = 9
        self.gpu.out = b"NVIDIA-SMI has failed because it couldn't communicate with the NVIDIA driver.\n"
        self.assertTrue(self.watch(420))
        message = self.assert_deallocated("GPU falhando na partida")
        self.assertIn("couldn't communicate with the NVIDIA driver", message)

    def test_nvidia_smi_writing_garbage_still_deallocates(self):
        self.gpu.code, self.gpu.err = 15, b"\xff\xfe GPU lost\n"
        self.assertTrue(self.watch(420))
        self.assert_deallocated("GPU falhando na partida")

    def test_missing_nvidia_smi_deallocates(self):
        self.gpu.missing = True
        self.assertTrue(self.watch(420))
        self.assert_deallocated("GPU falhando na partida")

    def test_nvidia_smi_listing_no_gpu_deallocates(self):
        self.gpu.out = b"\n"
        self.assertTrue(self.watch(420))
        self.assert_deallocated("GPU falhando na partida")

    def test_hung_nvidia_smi_deallocates_without_waiting_for_it(self):
        self.gpu.hangs = True
        self.assertTrue(self.watch(420))
        self.assertEqual(self.gpu.timeout, 60)
        self.assertTrue(self.gpu.killed)
        self.assertFalse(self.gpu.waited)
        self.assert_deallocated("GPU falhando na partida")


class Heartbeat(Pass):
    def test_fresh_heartbeat_is_silent(self):
        self.beat(age=60)
        self.assertTrue(self.watch(3600))
        self.assertEqual(self.gpu.started, [])
        self.assert_nothing_done()

    def test_heartbeat_exactly_15_min_old_still_counts(self):
        self.beat(age=900)
        self.assertTrue(self.watch(3600))
        self.assert_nothing_done()

    def test_heartbeat_older_than_15_min_deallocates(self):
        self.beat(age=901)
        self.assertTrue(self.watch(3600))
        self.assert_deallocated("heartbeat parado há 901 s")
        self.assertEqual(self.gpu.started, [])

    def test_no_heartbeat_at_15_min_deallocates(self):
        self.assertTrue(self.watch(900))
        self.assert_deallocated("sem heartbeat desde a partida")
        self.assertEqual(self.gpu.started, [])

    def test_heartbeat_from_before_boot_counts_as_none(self):
        # Started again after a deallocation: the file on the OS disk is from the last boot.
        self.beat(age=1000 + 30)
        self.assertTrue(self.watch(1000))
        self.assert_deallocated("sem heartbeat desde a partida")


class Maintenance(Pass):
    MALFORMED = (
        "",
        "amanhã\n",
        "2026-11-03 14:00:00Z\n",
        "2026-11-03T14:00:00\n",
        "2026-11-03T14:00:00+00:00\n",
        "2026-11-3T14:00:00Z\n",
        "2026-11-03T14:00:00Z\n2026-11-03T15:00:00Z\n",
        "2026-11-03T14:00:00Z\n\n",
        "2026-02-30T14:00:00Z\n",
    )

    def test_valid_marker_holds_the_gpu_check(self):
        self.mark("2026-11-03T14:00:00Z\n")
        self.gpu.code = 9
        self.assertTrue(self.watch(420))
        self.assertEqual(self.gpu.started, [])
        self.assertEqual(self.azure.requests, [])
        self.assertEqual(self.syslog.lines, [(syslog.LOG_INFO, "OK manutenção até 2026-11-03T14:00:00Z")])

    def test_valid_marker_holds_the_heartbeat_check(self):
        self.mark("2026-11-03T14:00:00Z")
        self.assertTrue(self.watch(3600))
        self.assertEqual(self.azure.requests, [])
        self.assertEqual(self.syslog.lines, [(syslog.LOG_INFO, "OK manutenção até 2026-11-03T14:00:00Z")])

    def test_deadline_exactly_4_h_after_writing_is_valid(self):
        self.mark("2026-11-03T15:50:00Z\n")
        self.assertTrue(self.watch(3600))
        self.assertEqual(self.azure.requests, [])

    def assert_ignored(self, reason):
        """Logged once as FALHA with the reason; the pass goes on as without a
        marker, and with no heartbeat at 1 h of uptime, VM2 is deallocated."""
        self.assertFalse(self.watch(3600))
        failures = [message for priority, message in self.syslog.lines if priority == syslog.LOG_ERR]
        self.assertEqual(len(failures), 1, self.syslog.lines)
        self.assertTrue(failures[0].startswith("FALHA "), failures[0])
        self.assertIn(reason, failures[0])
        self.assertEqual(len(self.azure.arm()), 1)

    def test_expired_marker_is_ignored(self):
        self.mark("2026-11-03T11:59:59Z\n")
        self.assert_ignored("vencido")

    def test_marker_ending_now_is_expired(self):
        self.mark("2026-11-03T12:00:00Z\n")
        self.assert_ignored("vencido")

    def test_deadline_beyond_4_h_after_writing_is_ignored(self):
        self.mark("2026-11-03T15:50:01Z\n")
        self.assert_ignored("4 h")

    def test_malformed_marker_is_ignored(self):
        for text in self.MALFORMED:
            with self.subTest(text=text):
                self.syslog.lines.clear()
                self.azure.requests.clear()
                self.mark(text)
                self.assert_ignored("formato")

    def test_unreadable_marker_is_ignored(self):
        os.mkdir(self.marker)
        self.assert_ignored("ilegível")

    def test_marker_that_is_not_text_is_ignored(self):
        with open(self.marker, "wb") as file:
            file.write(b"\xff\xfe2026-11-03T14:00:00Z\n")
        self.assert_ignored("ilegível")


class Deallocation(Pass):
    def test_asks_arm_with_vm2_identity_and_no_body(self):
        self.assertTrue(self.watch(900))
        [(imds, imds_timeout), (arm, arm_timeout)] = self.azure.requests
        self.assertEqual((imds.get_method(), imds.full_url), ("GET", IMDS))
        self.assertEqual(imds.get_header("Metadata"), "true")
        self.assertEqual((arm.get_method(), arm.full_url), ("POST", DEALLOCATE))
        self.assertEqual(arm.get_header("Authorization"), f"Bearer {TOKEN}")
        self.assertIsNone(arm.data)
        self.assertIsNotNone(imds_timeout)
        self.assertIsNotNone(arm_timeout)
        self.assertNotIn(TOKEN, repr(self.syslog.lines))

    def assert_failed(self, *details):
        [(priority, message)] = self.syslog.lines
        self.assertEqual(priority, syslog.LOG_ERR)
        self.assertTrue(message.startswith("FALHA "), message)
        for detail in ("sem heartbeat desde a partida", *details):
            self.assertIn(detail, message)
        self.assertNotIn(TOKEN, message)

    def test_imds_failure_logs_falha_and_fails(self):
        self.azure.imds_error = http_error(IMDS, 400, {"error": "invalid_request", "error_description": "Identity not found"})
        self.assertFalse(self.watch(900))
        self.assertEqual(self.azure.arm(), [])
        self.assert_failed("IMDS")

    def test_arm_refusal_logs_falha_with_the_status_and_fails(self):
        self.azure.arm_answer = http_error(DEALLOCATE, 403, {"error": {"code": "AuthorizationFailed", "message": "sem permissão"}})
        self.assertFalse(self.watch(900))
        self.assert_failed("403")

    def test_arm_out_of_reach_logs_falha_and_fails(self):
        self.azure.arm_answer = urllib.error.URLError(TimeoutError("timed out"))
        self.assertFalse(self.watch(900))
        self.assert_failed("timed out")


class Main(Pass):
    def run_main(self, uptime=None):
        if uptime is not None:
            with open(self.uptime_file, "w") as file:
                file.write(uptime)
        with mock.patch.object(watchdog.time, "time", return_value=NOW):
            return watchdog.main()

    def test_nothing_needed_exits_0_and_logs_to_local0_as_pathsol_watchdog(self):
        self.beat(age=30)
        self.assertEqual(self.run_main("1000.25 3001.50\n"), 0)
        self.assertEqual(self.syslog.opened, ("pathsol-watchdog", syslog.LOG_LOCAL0))
        self.assert_nothing_done()

    def test_uptime_is_the_first_field(self):
        # 420 s up (GPU window) and 1600 s idle: with no pulse, only the GPU is checked.
        self.assertEqual(self.run_main("420.00 1600.00\n"), 0)
        self.assertEqual(self.gpu.started, [GPU_CHECK])
        self.assert_nothing_done()

    def test_accepted_deallocation_exits_0(self):
        self.assertEqual(self.run_main("1000.25 3001.50\n"), 0)
        self.assert_deallocated("sem heartbeat desde a partida")

    def test_refused_deallocation_exits_1(self):
        self.azure.arm_answer = http_error(DEALLOCATE, 409, {"error": {"code": "OperationNotAllowed", "message": "x"}})
        self.assertEqual(self.run_main("1000.25 3001.50\n"), 1)

    def test_unexpected_failure_reaches_syslog_and_exits_1(self):
        self.assertEqual(self.run_main(uptime=None), 1)
        [(priority, message)] = self.syslog.lines
        self.assertEqual(priority, syslog.LOG_ERR)
        self.assertTrue(message.startswith("FALHA "), message)
        self.assertEqual(self.azure.requests, [])


if __name__ == "__main__":
    unittest.main()
