import base64
import hashlib
import io
import json
import os
import tempfile
import unittest
import urllib.parse
from unittest import mock
from xml.etree import ElementTree

from pathsol_worker import blob


class Response(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}


class Opener:
    """Fake IMDS and Blob: keeps the requests and answers from a script."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.requests = []

    def __call__(self, request, timeout=None):
        if request.full_url.startswith("http://169.254.169.254/"):
            return Response(json.dumps({"access_token": "tok", "expires_on": "9999999999"}).encode())
        self.requests.append(request)
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def b64(raw):
    return base64.b64encode(raw).decode()


class Download(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "l.svs")

    def test_streams_the_wsi_and_checks_its_sha256(self):
        content = b"wsi" * 1000
        opener = Opener(Response(content))
        blob.Blob(opener).download("wsi-publico", "x.svs", self.path, hashlib.sha256(content).hexdigest())
        with open(self.path, "rb") as f:
            self.assertEqual(f.read(), content)
        request = opener.requests[0]
        self.assertEqual(request.full_url, "https://pathsolwsiv3.blob.core.windows.net/wsi-publico/x.svs")
        self.assertEqual(request.get_header("Authorization"), "Bearer tok")

    def test_different_sha256_leaves_no_file(self):
        with self.assertRaises(blob.BlobError):
            blob.Blob(Opener(Response(b"outro"))).download("wsi-publico", "x.svs", self.path, "0" * 64)
        self.assertFalse(os.path.exists(self.path))


class Upload(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "j.h5")
        self.content = os.urandom(2500)
        with open(self.path, "wb") as f:
            f.write(self.content)
        self.md5 = hashlib.md5(self.content).digest()

    def head(self, size=None, md5=None):
        return Response(headers={"Content-Length": str(size or len(self.content)), "Content-MD5": md5 or b64(self.md5)})

    def test_blocks_with_their_md5_then_the_list_then_the_check(self):
        opener = Opener(Response(), Response(), Response(), Response(), self.head())
        with mock.patch.object(blob, "BLOCK", 1000):
            blob.Blob(opener).upload("t/s/h/j.h5", self.path, self.md5)
        blocks, commit, check = opener.requests[:3], opener.requests[3], opener.requests[4]
        for i, request in enumerate(blocks):
            query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
            self.assertEqual((request.get_method(), query["comp"]), ("PUT", ["block"]))
            self.assertEqual(request.get_header("Content-md5"), b64(hashlib.md5(self.content[i * 1000:(i + 1) * 1000]).digest()))
        self.assertTrue(commit.full_url.startswith("https://pathsolwsiv3.blob.core.windows.net/slide-h5/t/s/h/j.h5?"))
        self.assertIn("comp=blocklist", commit.full_url)
        self.assertEqual(commit.get_header("X-ms-blob-content-md5"), b64(self.md5))
        ids = [e.text for e in ElementTree.fromstring(commit.data)]
        sent = [urllib.parse.parse_qs(urllib.parse.urlsplit(r.full_url).query)["blockid"][0] for r in blocks]
        self.assertEqual(ids, sent)
        self.assertEqual(check.get_method(), "HEAD")

    def test_stored_blob_that_differs_is_an_error(self):
        for head in (self.head(size=1), self.head(md5=b64(b"x" * 16))):
            opener = Opener(Response(), Response(), head)
            with self.subTest(head=head.headers), self.assertRaises(blob.BlobError):
                blob.Blob(opener).upload("t/s/h/j.h5", self.path, self.md5)


if __name__ == "__main__":
    unittest.main()
