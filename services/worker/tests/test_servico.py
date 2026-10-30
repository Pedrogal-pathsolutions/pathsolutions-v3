import io
import json
import os
import tempfile
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


if __name__ == "__main__":
    unittest.main()
