import base64
import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.error
import urllib.parse
from unittest import mock

import enviar_modelo as enviar

REVISION = "31a3b9fee16554c8552cb643d311733bce8faf7c"


class Response(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}


def not_found():
    return urllib.error.HTTPError("u", 404, "The specified blob does not exist.", {}, None)


class Storage:
    """Fake IMDS and Blob, with the blobs already there."""

    def __init__(self, existing=None):
        self.existing = dict(existing or {})
        self.blocks = {}
        self.requests = []

    def __call__(self, request, timeout=None):
        if request.full_url.startswith("http://169.254.169.254/"):
            return Response(json.dumps({"access_token": "tok"}).encode())
        self.requests.append(request)
        name = urllib.parse.unquote(urllib.parse.urlsplit(request.full_url).path.split("/modelos/", 1)[1])
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        if query.get("comp") == ["block"]:
            self.blocks.setdefault(name, []).append(request.data)
        elif query.get("comp") == ["blocklist"]:
            self.existing[name] = b"".join(self.blocks.pop(name))
        if request.get_method() == "HEAD":
            if name not in self.existing:
                raise not_found()
            content = self.existing[name]
            return Response(headers={"Content-Length": str(len(content)),
                                     "Content-MD5": base64.b64encode(hashlib.md5(content).digest()).decode()})
        return Response()


class Send(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.files = {"model.safetensors": os.urandom(2500), "config.json": b"{}"}
        for name, content in self.files.items():
            with open(os.path.join(self.dir.name, name), "wb") as f:
                f.write(content)
        manifest = {"revision": REVISION, "files": {n: {"size": len(c), "sha256": hashlib.sha256(c).hexdigest()}
                                                    for n, c in self.files.items()}}
        with open(os.path.join(self.dir.name, "manifesto.json"), "w") as f:
            json.dump(manifest, f)

    def run_main(self, storage):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(enviar, "urlopen", storage), mock.patch.object(enviar, "BLOCK", 1000), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = enviar.main(["--origem", self.dir.name])
        return code, out.getvalue() + err.getvalue()

    def test_every_file_and_the_manifest_go_create_only(self):
        storage = Storage()
        code, output = self.run_main(storage)
        self.assertEqual(code, 0)
        commits = [r for r in storage.requests if "comp=blocklist" in r.full_url]
        self.assertEqual(len(commits), 3)
        for commit in commits:
            self.assertEqual(commit.get_header("If-none-match"), "*")
            self.assertIsNotNone(commit.get_header("X-ms-blob-content-md5"))
            self.assertIn(f"/modelos/hibou-L/{REVISION}/", commit.full_url)
        blocks = [r for r in storage.requests if "comp=block&" in r.full_url or r.full_url.endswith("comp=block")]
        self.assertTrue(all(r.get_header("Content-md5") for r in blocks))
        self.assertNotIn("tok", output)

    def test_a_file_that_differs_from_the_manifest_stops_everything(self):
        with open(os.path.join(self.dir.name, "config.json"), "wb") as f:
            f.write(b"{ }")
        storage = Storage()
        code, output = self.run_main(storage)
        self.assertEqual(code, 1)
        self.assertEqual(storage.requests, [])
        self.assertIn("FALHA", output)

    def test_same_file_already_there_counts_as_sent(self):
        name = f"hibou-L/{REVISION}/model.safetensors"
        storage = Storage({name: self.files["model.safetensors"]})
        code, _ = self.run_main(storage)
        self.assertEqual(code, 0)
        self.assertFalse([r for r in storage.requests if name in urllib.parse.unquote(r.full_url) and r.get_method() == "PUT"])

    def test_different_file_already_there_is_never_overwritten(self):
        name = f"hibou-L/{REVISION}/config.json"
        storage = Storage({name: b"outro"})
        code, output = self.run_main(storage)
        self.assertEqual(code, 1)
        self.assertFalse([r for r in storage.requests if name in urllib.parse.unquote(r.full_url) and r.get_method() == "PUT"])
        self.assertIn("FALHA", output)


if __name__ == "__main__":
    unittest.main()
