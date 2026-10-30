import base64
import contextlib
import hashlib
import hmac
import io
import os
import subprocess
import tempfile
import unittest
import urllib.parse
from unittest import mock
from xml.etree import ElementTree

import pathsol_enviar_lamina as enviar

KEY = base64.b64encode(b"k" * 32).decode()
DELEGATION = f"""<?xml version="1.0" encoding="utf-8"?><UserDelegationKey><SignedOid>oid-vm1</SignedOid>
<SignedTid>tid</SignedTid><SignedStart>2026-10-30T20:00:00Z</SignedStart><SignedExpiry>2026-10-30T21:00:00Z</SignedExpiry>
<SignedService>b</SignedService><SignedVersion>2026-02-06</SignedVersion><Value>{KEY}</Value></UserDelegationKey>""".encode()


class Response(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}


class Storage:
    def __init__(self):
        self.requests, self.blocks, self.blobs = [], [], {}

    def __call__(self, request, timeout=None):
        url = request.full_url
        if url.startswith("http://169.254.169.254/"):
            return Response(b'{"access_token": "tok-vm1"}')
        self.requests.append(request)
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
        if query.get("comp") == ["userdelegationkey"]:
            return Response(DELEGATION)
        if query.get("comp") == ["block"]:
            self.blocks.append(request.data)
        elif query.get("comp") == ["blocklist"]:
            self.blobs[urllib.parse.urlsplit(url).path] = b"".join(self.blocks)
        elif request.get_method() == "HEAD":
            content = self.blobs[urllib.parse.urlsplit(url).path]
            return Response(headers={"Content-Length": str(len(content)),
                                     "Content-MD5": base64.b64encode(hashlib.md5(content).digest()).decode()})
        return Response()


class Send(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.staging = os.path.join(self.dir.name, "aceite")
        os.makedirs(self.staging)
        self.original = os.path.join(self.staging, "caso-12345 paciente.svs")
        with open(self.original, "wb") as f:
            f.write(b"lamina original")
        self.registered = []

    def deidentify(self, source, target):
        with open(target, "xb") as f:
            f.write(b"lamina desidentificada")
        return 2

    def producer(self, args, **kwargs):
        self.registered.append(args)
        return subprocess.CompletedProcess(args, 0, stdout="OK", stderr="")

    def run_main(self, storage, *extra):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(enviar, "STAGING", self.staging), mock.patch.object(enviar, "urlopen", storage), \
                mock.patch.object(enviar.desidentificar, "deidentify", self.deidentify), \
                mock.patch.object(enviar, "run", self.producer), mock.patch.object(enviar, "BLOCK", 8), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = enviar.main(["--tenant", "publico", "--arquivo", self.original, "--material", "biopsia",
                                "--coloracao", "HE", *extra])
        return code, out.getvalue() + err.getvalue()

    def test_deidentified_copy_goes_create_only_and_is_registered(self):
        storage = Storage()
        code, output = self.run_main(storage, "--orgao", "estomago")
        self.assertEqual(code, 0)
        put_blocks = [r for r in storage.requests if "comp=block&" in r.full_url]
        commit = [r for r in storage.requests if "comp=blocklist" in r.full_url][0]
        for request in put_blocks + [commit]:
            self.assertIsNone(request.get_header("Authorization"))  # the SAS authorizes, not VM1's token
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
            self.assertEqual((query["sp"], query["sr"], query["spr"], query["sv"]), (["c"], ["b"], ["https"], ["2026-02-06"]))
            self.assertEqual(request.get_header("X-ms-version"), "2026-04-06")
        self.assertEqual(commit.get_header("If-none-match"), "*")
        path = urllib.parse.urlsplit(commit.full_url).path
        self.assertRegex(path, r"^/wsi-publico/[0-9a-f-]{36}\.svs$")
        self.assertEqual(storage.blobs[path], b"lamina desidentificada")
        head = [r for r in storage.requests if r.get_method() == "HEAD"][0]
        self.assertEqual(head.get_header("Authorization"), "Bearer tok-vm1")
        slide = path.rsplit("/", 1)[1].split(".")[0]
        sha = hashlib.sha256(b"lamina desidentificada").hexdigest()
        call = self.registered[0]
        self.assertEqual(call[call.index("lamina"):], ["lamina", "--tenant", "publico", "--arquivo", f"{slide}.svs",
                                                       "--sha256", sha, "--material", "biopsia", "--coloracao", "HE",
                                                       "--orgao", "estomago"])
        self.assertEqual(os.listdir(self.staging), [])
        self.assertIn(slide, output)
        self.assertIn(sha, output)
        for secret in ("caso-12345", "paciente", "tok-vm1", KEY):
            self.assertNotIn(secret, output)

    def test_files_outside_the_staging_are_refused(self):
        outside = os.path.join(self.dir.name, "fora.svs")
        with open(outside, "wb") as f:
            f.write(b"x")
        self.original = outside
        storage = Storage()
        code, _ = self.run_main(storage)
        self.assertNotEqual(code, 0)
        self.assertEqual(storage.requests, [])

    def test_staging_over_its_cap_is_refused(self):
        storage = Storage()
        with mock.patch.object(enviar, "STAGING_CAP", 4):
            code, output = self.run_main(storage)
        self.assertEqual(code, 1)
        self.assertIn("teto", output)
        self.assertEqual(storage.requests, [])

    def test_a_stored_blob_that_differs_keeps_the_staging_files(self):
        class Wrong(Storage):
            def __call__(self, request, timeout=None):
                response = super().__call__(request, timeout)
                if request.get_method() == "HEAD":
                    response.headers["Content-Length"] = "1"
                return response

        code, output = self.run_main(Wrong())
        self.assertEqual(code, 1)
        self.assertIn("FALHA", output)
        self.assertEqual(self.registered, [])
        self.assertIn("caso-12345 paciente.svs", os.listdir(self.staging))


class Signature(unittest.TestCase):
    def test_string_to_sign_of_version_2025_07_05_and_later(self):
        key = enviar.DelegationKey("oid", "tid", "2026-10-30T20:00:00Z", "2026-10-30T21:00:00Z", "b", "2026-02-06", KEY)
        text = enviar.string_to_sign("c", "2026-10-30T20:00:00Z", "2026-10-30T21:00:00Z", "/blob/conta/wsi-publico/x.svs", key)
        lines = text.split("\n")
        self.assertEqual(len(lines), 26)
        self.assertEqual(lines[:10], ["c", "2026-10-30T20:00:00Z", "2026-10-30T21:00:00Z", "/blob/conta/wsi-publico/x.svs",
                                      "oid", "tid", "2026-10-30T20:00:00Z", "2026-10-30T21:00:00Z", "b", "2026-02-06"])
        self.assertEqual(lines[15:19], ["", "https", "2026-02-06", "b"])
        self.assertEqual(set(lines[10:15] + lines[19:]), {""})

    def test_signature_is_the_hmac_of_that_string_with_the_delegation_key(self):
        key = enviar.DelegationKey("oid", "tid", "s", "e", "b", "2026-02-06", KEY)
        query = urllib.parse.parse_qs(enviar.sas("wsi-publico", "x.svs", key, "2026-10-30T20:00:00Z", "2026-10-30T21:00:00Z"))
        expected = hmac.new(base64.b64decode(KEY), enviar.string_to_sign(
            "c", "2026-10-30T20:00:00Z", "2026-10-30T21:00:00Z", "/blob/pathsolwsiv3/wsi-publico/x.svs", key).encode(), "sha256").digest()
        self.assertEqual(query["sig"], [base64.b64encode(expected).decode()])
        self.assertEqual(query["skoid"], ["oid"])


if __name__ == "__main__":
    unittest.main()
