import contextlib
import hashlib
import io
import json
import os
import tempfile
import unittest
from unittest import mock

import baixar_hibou as hibou

TOKEN = "hf_tokenquenuncaaparece"


def lfs_entry(name, content):
    return {"rfilename": name, "size": len(content), "lfs": {"sha256": hashlib.sha256(content).hexdigest(), "size": len(content)}}


def git_entry(name, content):
    blob = hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()
    return {"rfilename": name, "size": len(content), "blobId": blob}


WEIGHTS = b"pesos" * 1000
CODE = b"class Dinov2ModelWithRegisters: pass\n"
CARD = b"---\nlicense: apache-2.0\n---\n"


def revision_info(**changes):
    info = {
        "sha": hibou.REVISION,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            lfs_entry("model.safetensors", WEIGHTS),
            git_entry("modeling_dinov2.py", CODE),
            git_entry("README.md", CARD),
        ],
    }
    info.update(changes)
    return info


class FakeHub:
    """Answers the API call and the file downloads from memory."""

    def __init__(self, info, files):
        self.info = info
        self.files = files
        self.requests = []

    def __call__(self, request):
        self.requests.append(request)
        url = request.full_url
        if url.startswith("https://huggingface.co/api/"):
            return io.BytesIO(json.dumps(self.info).encode())
        name = url.rsplit("/", 1)[1]
        return io.BytesIO(self.files[name])


PINS = {"model.safetensors": hashlib.sha256(WEIGHTS).hexdigest()}
FILES = {"model.safetensors": WEIGHTS, "modeling_dinov2.py": CODE, "README.md": CARD}


class GitBlobSha1(unittest.TestCase):
    def test_matches_git_hash_object(self):
        # `printf 'hello\n' | git hash-object --stdin`
        self.assertEqual(hibou.git_blob_sha1(b"hello\n"), "ce013625030ba8dba906f756967f9e9ca394464a")


class Request(unittest.TestCase):
    def test_token_is_not_sent_on_redirects(self):
        request = hibou.authorized(hibou.FILE_URL.format(path="model.safetensors"), TOKEN)
        self.assertEqual(request.unredirected_hdrs.get("Authorization"), f"Bearer {TOKEN}")
        self.assertNotIn("Authorization", request.headers)

    def test_urls_point_to_the_pinned_revision(self):
        self.assertIn(hibou.REVISION, hibou.API_URL)
        self.assertIn(f"/resolve/{hibou.REVISION}/", hibou.FILE_URL)


class Download(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.dest = self.root.name

    def tearDown(self):
        self.root.cleanup()

    def run_download(self, hub, pins=PINS):
        return hibou.download_revision(hub, TOKEN, self.dest, pins=pins)

    def listing(self):
        return sorted(os.listdir(os.path.join(self.dest, hibou.REVISION)))

    def test_writes_every_file_and_the_manifest(self):
        manifest = self.run_download(FakeHub(revision_info(), FILES))
        self.assertEqual(self.listing(), ["README.md", "manifesto.json", "model.safetensors", "modeling_dinov2.py"])
        with open(os.path.join(self.dest, hibou.REVISION, "model.safetensors"), "rb") as f:
            self.assertEqual(f.read(), WEIGHTS)
        self.assertEqual(manifest["revision"], hibou.REVISION)
        self.assertEqual(manifest["license"], "apache-2.0")
        self.assertEqual(manifest["files"]["model.safetensors"]["sha256"], hashlib.sha256(WEIGHTS).hexdigest())
        with open(os.path.join(self.dest, hibou.REVISION, "manifesto.json")) as f:
            self.assertEqual(json.load(f), manifest)

    def test_refuses_another_revision(self):
        with self.assertRaises(hibou.Refused):
            self.run_download(FakeHub(revision_info(sha="0" * 40), FILES))
        self.assertFalse(os.path.exists(os.path.join(self.dest, hibou.REVISION)))

    def test_refuses_weights_that_differ_from_the_plan(self):
        # The API itself may change; the pinned sha256 from the plan decides.
        with self.assertRaises(hibou.Refused):
            self.run_download(FakeHub(revision_info(), FILES), pins={"model.safetensors": "f" * 64})

    def test_refuses_when_pinned_weights_are_missing(self):
        info = revision_info(siblings=[git_entry("README.md", CARD)])
        with self.assertRaises(hibou.Refused):
            self.run_download(FakeHub(info, FILES))

    def test_corrupted_file_leaves_nothing_behind(self):
        files = dict(FILES, **{"modeling_dinov2.py": b"import os; os.system('x')\n"})
        with self.assertRaises(hibou.Refused):
            self.run_download(FakeHub(revision_info(), files))
        self.assertNotIn("modeling_dinov2.py", self.listing())
        self.assertFalse([name for name in self.listing() if name.startswith(".parcial")])
        self.assertNotIn("manifesto.json", self.listing())

    def test_refuses_names_outside_the_directory(self):
        for name in ("../fora.py", "sub/dir.py", "/etc/passwd", ".."):
            info = revision_info(siblings=revision_info()["siblings"] + [git_entry(name, CODE)])
            with self.subTest(name=name), self.assertRaises(hibou.Refused):
                self.run_download(FakeHub(info, dict(FILES, **{name.rsplit("/", 1)[-1]: CODE})))

    def test_refuses_a_revision_bigger_than_the_cap(self):
        info = revision_info()
        info["siblings"][0] = dict(info["siblings"][0], size=hibou.MAX_TOTAL_BYTES + 1)
        with self.assertRaises(hibou.Refused):
            self.run_download(FakeHub(info, FILES))

    def test_skips_files_already_verified(self):
        self.run_download(FakeHub(revision_info(), FILES))
        hub = FakeHub(revision_info(), FILES)
        self.run_download(hub)
        self.assertEqual([r.full_url for r in hub.requests], [hibou.API_URL])

    def test_stops_on_an_existing_file_that_does_not_match(self):
        os.makedirs(os.path.join(self.dest, hibou.REVISION))
        with open(os.path.join(self.dest, hibou.REVISION, "README.md"), "wb") as f:
            f.write(b"outro\n")
        with self.assertRaises(hibou.Refused):
            self.run_download(FakeHub(revision_info(), FILES))
        with open(os.path.join(self.dest, hibou.REVISION, "README.md"), "rb") as f:
            self.assertEqual(f.read(), b"outro\n")


class Main(unittest.TestCase):
    def test_token_never_reaches_the_output(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        out, err = io.StringIO(), io.StringIO()
        hub = FakeHub(revision_info(), FILES)
        with mock.patch.object(hibou, "PINS", PINS), mock.patch("getpass.getpass", return_value=TOKEN), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = hibou.main(["--destino", root.name], opener=hub)
        self.assertEqual(code, 0)
        self.assertNotIn(TOKEN, out.getvalue() + err.getvalue())
        self.assertIn("model.safetensors", out.getvalue())

    def test_failure_message_has_no_token(self):
        root = tempfile.TemporaryDirectory()
        self.addCleanup(root.cleanup)
        out, err = io.StringIO(), io.StringIO()
        hub = FakeHub(revision_info(sha="0" * 40), FILES)
        with mock.patch("getpass.getpass", return_value=TOKEN), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = hibou.main(["--destino", root.name], opener=hub)
        self.assertEqual(code, 1)
        self.assertIn("FALHA", err.getvalue())
        self.assertNotIn(TOKEN, out.getvalue() + err.getvalue())


if __name__ == "__main__":
    unittest.main()
