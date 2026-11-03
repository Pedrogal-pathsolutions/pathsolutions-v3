import datetime
import io
import json
import os
import tempfile
import time
import unittest

from pathsol_worker import fila, servico


class Response(io.BytesIO):
    pass


class Vault:
    def __init__(self):
        self.urls = []

    def __call__(self, request, timeout=None):
        self.urls.append(request.full_url)
        if request.full_url.startswith("http://169.254.169.254/"):
            return Response(json.dumps({"access_token": "tok", "expires_on": "9999999999"}).encode())
        self.auth = request.get_header("Authorization")
        return Response(json.dumps({"value": "senha-secreta", "id": "x"}).encode())


class Password(unittest.TestCase):
    def test_reads_the_worker_secret_with_a_vault_token(self):
        vault = Vault()
        self.assertEqual(servico.db_password(vault), "senha-secreta")
        self.assertIn("resource=https%3A%2F%2Fvault.azure.net", vault.urls[0])
        self.assertTrue(vault.urls[1].startswith("https://pathsol-kv-v3.vault.azure.net/secrets/banco-worker?api-version="))
        self.assertEqual(vault.auth, "Bearer tok")


class WorkRoot(unittest.TestCase):
    def test_start_empties_what_a_dead_job_left(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, "job-velho"))
            with open(os.path.join(root, "job-velho", "lamina.svs"), "wb") as f:
                f.write(b"x")
            servico.empty(root)
            self.assertEqual(os.listdir(root), [])


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class Jobs:
    def __init__(self, texts):
        self.texts = list(texts)
        self.timeouts = []

    def get(self, visibility_timeout):
        self.timeouts.append(visibility_timeout)
        return fila.Received("m", "p", self.texts.pop(0), 1) if self.texts else None


class Loop(unittest.TestCase):
    def test_takes_jobs_until_the_queue_stays_idle(self):
        clock = Clock()
        jobs = Jobs(["a", "b"])
        handled = []

        def handle(received, *_):
            handled.append(received.text)
            if received.text == "b":
                raise OSError("banco fora do ar")  # logged; the message comes back after the timeout
            return "COMPLETED"

        servico.run(jobs, None, None, None, visibility=1800, idle=600, clock=clock, sleep=clock.sleep, handle=handle)
        self.assertEqual(handled, ["a", "b"])
        self.assertEqual(set(jobs.timeouts), {1800})
        self.assertGreaterEqual(clock.now, 600)

    def test_beats_before_every_poll(self):
        clock = Clock()
        jobs = Jobs(["a"])
        beats = []
        servico.run(jobs, None, None, None, visibility=1800, idle=600, pulse=lambda: beats.append(clock.now),
                    clock=clock, sleep=clock.sleep, handle=lambda *_: "COMPLETED")
        self.assertEqual(len(beats), len(jobs.timeouts))

    def test_takes_no_job_when_it_could_pass_vm1_shutdown(self):
        clock = Clock()
        jobs = Jobs(["a"])
        servico.run(jobs, None, None, None, visibility=1800, idle=600, accepting=lambda: False,
                    clock=clock, sleep=clock.sleep, handle=lambda *_: self.fail("pegou job"))
        self.assertEqual(jobs.timeouts, [])
        self.assertGreaterEqual(clock.now, 600)


class Beating(unittest.TestCase):
    def test_beats_during_a_job(self):
        beats = []
        with servico.beating(lambda: beats.append(1), limit=60, every=0.01):
            time.sleep(0.2)
        self.assertGreater(len(beats), 3)

    def test_a_job_past_the_visibility_timeout_stops_beating(self):
        beats = []
        with servico.beating(lambda: beats.append(1), limit=0.05, every=0.01):
            time.sleep(0.1)
            seen = len(beats)
            time.sleep(0.1)
        self.assertEqual(len(beats), seen)
        self.assertLess(seen, 6)


class Leave(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.marker = os.path.join(self.dir.name, "manutencao")
        self.now = datetime.datetime(2026, 11, 3, 12, 0, tzinfo=datetime.UTC)
        self.calls = []

    def tearDown(self):
        self.dir.cleanup()

    def deallocate(self):
        self.calls.append("desalocar")
        return 202

    def write(self, text):
        with open(self.marker, "w") as f:
            f.write(text)
        os.utime(self.marker, (self.now.timestamp(), self.now.timestamp()))

    def test_an_idle_queue_deallocates_vm2(self):
        self.assertEqual(servico.leave(self.marker, self.now, self.deallocate), 202)
        self.assertEqual(self.calls, ["desalocar"])

    def test_maintenance_keeps_vm2_on(self):
        self.write("2026-11-03T14:00:00Z")
        self.assertIsNone(servico.leave(self.marker, self.now, self.deallocate))
        self.assertEqual(self.calls, [])

    def test_a_bad_marker_does_not_keep_vm2_on(self):
        self.write("2026-11-03T18:00:00Z")
        with self.assertLogs("pathsol_worker", "ERROR"):
            servico.leave(self.marker, self.now, self.deallocate)
        self.assertEqual(self.calls, ["desalocar"])


class Touch(unittest.TestCase):
    def test_creates_the_file_and_refreshes_its_mtime(self):
        with tempfile.TemporaryDirectory() as root:
            path = os.path.join(root, "pulso")
            servico.touch(path)
            os.utime(path, (1, 1))
            servico.touch(path)
            self.assertGreater(os.stat(path).st_mtime, 1)


if __name__ == "__main__":
    unittest.main()
