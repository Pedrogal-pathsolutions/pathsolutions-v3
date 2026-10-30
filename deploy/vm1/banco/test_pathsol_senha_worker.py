import base64
import contextlib
import io
import json
import subprocess
import unittest
from unittest import mock

import pathsol_senha_worker as senha

TOKEN = "tok-da-vm1"


class Calls:
    def __init__(self, fail_vault=False):
        self.log = []
        self.fail_vault = fail_vault

    def run(self, args, **kwargs):
        self.log.append(("psql", args, kwargs.get("input")))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    def open(self, request, timeout=None):
        if request.full_url.startswith("http://169.254.169.254/"):
            self.log.append(("imds", request.full_url, None))
            return io.BytesIO(json.dumps({"access_token": TOKEN}).encode())
        self.log.append(("cofre", request, request.data))
        if self.fail_vault:
            raise senha.urllib.error.URLError("sem rede")
        return io.BytesIO(b"{}")


def run_main(calls):
    out, err = io.StringIO(), io.StringIO()
    with mock.patch.object(senha, "run", calls.run), mock.patch.object(senha, "urlopen", calls.open), \
            mock.patch.object(senha.secrets, "token_urlsafe", return_value="senha-de-teste"), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = senha.main([])
    return code, out.getvalue() + err.getvalue()


class Rotate(unittest.TestCase):
    def test_vault_first_then_the_role_with_a_verifier(self):
        calls = Calls()
        code, output = run_main(calls)
        self.assertEqual(code, 0)
        self.assertEqual([kind for kind, *_ in calls.log], ["imds", "cofre", "psql"])
        _, request, body = calls.log[1]
        self.assertEqual(request.get_method(), "PUT")
        self.assertTrue(request.full_url.startswith("https://pathsol-kv-v3.vault.azure.net/secrets/banco-worker?"))
        self.assertIn("resource=https%3A%2F%2Fvault.azure.net", calls.log[0][1])
        self.assertEqual(json.loads(body)["value"], "senha-de-teste")
        _, args, sql = calls.log[2]
        self.assertEqual(args[:6], ["docker", "exec", "-i", "-u", "postgres", "pathsol-banco"])
        # The verifier goes by stdin: a command line is visible to every user of VM1.
        self.assertTrue(sql.startswith("ALTER ROLE pathsol_worker LOGIN PASSWORD 'SCRAM-SHA-256$4096:"))
        self.assertNotIn("SCRAM", " ".join(args))
        self.assertNotIn("senha-de-teste", " ".join(args) + sql + output)
        self.assertNotIn(TOKEN, output)

    def test_vault_failure_leaves_the_role_untouched(self):
        calls = Calls(fail_vault=True)
        code, output = run_main(calls)
        self.assertEqual(code, 1)
        self.assertNotIn("psql", [kind for kind, *_ in calls.log])
        self.assertNotIn("senha-de-teste", output)


class Verifier(unittest.TestCase):
    def test_known_parts(self):
        salt = b"0123456789abcdef"
        verifier = senha.scram_verifier("abc", salt, 4096)
        method, rest = verifier.split("$", 1)
        iterations_salt, keys = rest.split("$")
        self.assertEqual(method, "SCRAM-SHA-256")
        self.assertEqual(iterations_salt, f"4096:{base64.b64encode(salt).decode()}")
        stored, server = keys.split(":")
        self.assertEqual(len(base64.b64decode(stored)), 32)
        self.assertEqual(len(base64.b64decode(server)), 32)


if __name__ == "__main__":
    unittest.main()
