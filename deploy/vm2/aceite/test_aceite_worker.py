"""The worker's acceptance tool (tests 1 and 6) against synthetic slides and .h5 files.

Runs in the worker test image, which has tifffile, with the worktree's worker code first on the path:

    docker run --rm --network none -v "$PWD/services/worker/src:/worker:ro" \
        -v "$PWD/services/worker/tests:/wtests:ro" -v "$PWD/deploy/vm2/aceite:/aceite:ro" \
        -e PYTHONPATH=/worker:/wtests:/aceite pathsol-worker-teste:dev \
        unittest discover -s /aceite -p 'test_aceite_worker.py'
"""
import base64
import collections
import contextlib
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
import urllib.error
import urllib.parse
import uuid
from unittest import mock

import h5py
import numpy as np
from PIL import Image

import aceite_worker
import sinteticas
from pathsol_worker import h5, passagem, qc

TENANT, SLIDE = str(uuid.uuid4()), str(uuid.uuid4())
HASH = "0123456789ab"
VERSION = '{"extrator":"teste"}'
# Ten by five patches of 224 px from the origin, row by row, as the worker's grid.
GRID = [(x, y) for y in range(0, 5 * 224, 224) for x in range(0, 10 * 224, 224)]
Usage = collections.namedtuple("Usage", "total used free")
PINK = (200, 120, 170)


class Response(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}


def md5_b64(content):
    return base64.b64encode(hashlib.md5(content).digest()).decode()


class Azure:
    """IMDS and the Blob service, each blob a local file; keeps the Blob requests.

    The GET of a broken blob raises its exception, after noting the files then in the work directory;
    a damaged one arrives with one bit flipped at the given offset.
    """

    def __init__(self, blobs, broken=None, damaged=None):
        self.blobs = blobs
        self.broken = broken or {}
        self.damaged = damaged or {}
        self.requests = []
        self.files_at_failure = None

    def __call__(self, request, timeout=None):
        if request.full_url.startswith("http://169.254.169.254/"):
            return Response(json.dumps({"access_token": "tok", "expires_on": "9999999999"}).encode())
        path = urllib.parse.unquote(urllib.parse.urlsplit(request.full_url).path)[1:]
        self.requests.append((request.get_method(), path))
        with open(self.blobs[path], "rb") as f:
            content = f.read()
        if request.get_method() == "HEAD":
            return Response(headers={"Content-Length": str(len(content)), "Content-MD5": md5_b64(content)})
        if path in self.broken:
            self.files_at_failure = [name for _, _, names in os.walk(aceite_worker.WORK) for name in names]
            raise self.broken[path]
        if path in self.damaged:
            content = bytearray(content)
            content[self.damaged[path]] ^= 1
        return Response(bytes(content))


def attrs(**changes):
    return {"tenant_id": TENANT, "slide_id": SLIDE, "wsi_sha256": "a" * 64, "extractor": "histai/hibou-L@x",
            "extractor_version": VERSION, "qc_version": "{}", "versions": "{}",
            "created_at": "2026-11-06T12:00:00+00:00", **changes}


def write_h5(path, coords, embeddings, **changes):
    """A .h5 of the contract, by pathsol_worker.h5, with these patches and embeddings."""
    n = len(coords)
    tiles = passagem.Tiles(np.array(coords, dtype=np.int32), np.full((n, 3), 0.9, dtype=np.float32),
                           np.zeros((n, 224, 224, 3), dtype=np.uint8), 224, 0, qc.Focus(False, 0.0, 1.0, 1.0, None),
                           1.0, 0.5, "openslide.mpp-x/mpp-y", "openslide 4.0.1 (openslide-python 1.4.6)")
    h5.write(path, embeddings, tiles, attrs(**changes))


def tissue_box_slide(path):
    """4096 x 2048 px at 0.5 µm/px: glass, and flat tissue on the cells x 4 to 9, y 2 to 5 of the 224 px grid."""
    image = np.full((2048, 4096, 3), 240, dtype=np.uint8)
    image[448:1344, 896:2240] = PINK
    sinteticas.write_svs(path, image, mpp=0.5)
    return path


def rotated(rows, cosine, rng):
    """Rows at exactly this cosine to the given ones."""
    rows = rows.astype(np.float64)
    other = rng.normal(size=rows.shape)
    other -= (other * rows).sum(axis=1, keepdims=True) / (rows * rows).sum(axis=1, keepdims=True) * rows
    unit = rows / np.linalg.norm(rows, axis=1, keepdims=True)
    normal = other / np.linalg.norm(other, axis=1, keepdims=True)
    return (cosine * unit + np.sqrt(1 - cosine**2) * normal).astype(np.float32)


class Tool(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.work = os.path.join(self.dir.name, "trabalho")
        os.makedirs(self.work)
        patcher = mock.patch.object(aceite_worker, "WORK", self.work)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.blobs = {}
        self.rng = np.random.default_rng(0)

    def run_tool(self, *argv, azure=None):
        azure = azure or Azure(self.blobs)
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = aceite_worker.main(list(argv), aceite_worker.Storage(azure))
        return code, out.getvalue(), err.getvalue(), azure

    def h5_blob(self, coords, embeddings, **attrs):
        """Writes a .h5 and serves it in slide-h5; its blob name."""
        name = f"{TENANT}/{SLIDE}/{HASH}/{uuid.uuid4()}.h5"
        path = os.path.join(self.dir.name, f"{len(self.blobs)}.h5")
        write_h5(path, coords, embeddings, **attrs)
        self.blobs[f"slide-h5/{name}"] = path
        return name

    def compare(self, a, b, azure=None):
        code, out, err, azure = self.run_tool("comparar", "--h5", a, "--h5", b, azure=azure)
        return code, (json.loads(out) if out else None), err, azure


class Compare(Tool):
    def test_the_same_patches_in_another_order_with_close_embeddings_pass(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        order = self.rng.permutation(50)
        a = self.h5_blob(GRID, embeddings)
        b = self.h5_blob([GRID[i] for i in order], rotated(embeddings, 0.99999, self.rng)[order])
        code, result, _, _ = self.compare(a, b)
        self.assertEqual((code, result["veredito"]), (0, "OK"))
        self.assertEqual((result["mesma_lamina"], result["mesmo_extractor_version"]), (True, True))
        self.assertEqual((result["patches"], result["comuns"]), ([50, 50], 50))
        self.assertEqual((result["so_no_primeiro"], result["so_no_segundo"]), (0, 0))
        self.assertAlmostEqual(result["cosseno"]["media"], 0.99999, places=6)
        self.assertAlmostEqual(result["cosseno"]["minimo"], 0.99999, places=6)
        self.assertFalse(result["cosseno"]["nan_inf"])
        self.assertEqual(os.listdir(self.work), [])

    def test_the_verdict_follows_the_mean_cosine_against_0_999(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        a = self.h5_blob(GRID, embeddings)
        for cosine, expected in ((0.9992, (0, "OK")), (0.9988, (1, "FALHA"))):
            with self.subTest(cosine=cosine):
                code, result, _, _ = self.compare(a, self.h5_blob(GRID, rotated(embeddings, cosine, self.rng)))
                self.assertEqual((code, result["veredito"]), expected)
                self.assertAlmostEqual(result["cosseno"]["media"], cosine, places=6)

    def test_one_distant_patch_shows_in_the_minimum_but_the_mean_decides(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        other = embeddings.copy()
        other[7] = rotated(embeddings[7:8], 0.99, self.rng)[0]
        code, result, _, _ = self.compare(self.h5_blob(GRID, embeddings), self.h5_blob(GRID, other))
        self.assertEqual((code, result["veredito"]), (0, "OK"))
        self.assertAlmostEqual(result["cosseno"]["minimo"], 0.99, places=6)
        self.assertAlmostEqual(result["cosseno"]["media"], (49 + 0.99) / 50, places=6)

    def test_a_changed_set_of_patches_fails_and_shows_the_difference(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        a = self.h5_blob(GRID, embeddings)
        cases = (
            ("trocado", [(2240, 0)] + GRID[1:], embeddings, [50, 50], (1, 1), ([[0, 0]], [[2240, 0]])),
            ("a menos", GRID[1:], embeddings[1:], [50, 49], (1, 0), ([[0, 0]], [])),
        )
        for case, coords, rows, counts, only, examples in cases:
            with self.subTest(case=case):
                code, result, _, _ = self.compare(a, self.h5_blob(coords, rows))
                self.assertEqual((code, result["veredito"]), (1, "FALHA"))
                self.assertEqual((result["patches"], result["comuns"]), (counts, 49))
                self.assertEqual((result["so_no_primeiro"], result["so_no_segundo"]), only)
                self.assertEqual((result["exemplos_so_no_primeiro"], result["exemplos_so_no_segundo"]), examples)
                # The 49 patches in common have the same embeddings: only the set fails.
                self.assertAlmostEqual(result["cosseno"]["media"], 1.0, places=6)

    def test_another_tenant_slide_or_extractor_version_fails(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        a = self.h5_blob(GRID, embeddings)
        cases = (
            ("tenant", {"tenant_id": str(uuid.uuid4())}, (False, True)),
            ("lâmina", {"slide_id": str(uuid.uuid4())}, (False, True)),
            ("versão", {"extractor_version": '{"extrator":"outro"}'}, (True, False)),
        )
        for case, attrs, flags in cases:
            with self.subTest(case=case):
                code, result, _, _ = self.compare(a, self.h5_blob(GRID, embeddings, **attrs))
                self.assertEqual((code, result["veredito"]), (1, "FALHA"))
                self.assertEqual((result["mesma_lamina"], result["mesmo_extractor_version"]), flags)

    def test_no_patch_in_common_fails_without_a_cosine(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        shifted = [(x + 1, y) for x, y in GRID]
        code, result, err, _ = self.compare(self.h5_blob(GRID, embeddings), self.h5_blob(shifted, embeddings))
        self.assertEqual((code, result["veredito"]), (1, "FALHA"))
        self.assertEqual((result["comuns"], result["so_no_primeiro"], result["so_no_segundo"]), (0, 50, 50))
        self.assertEqual(result["exemplos_so_no_primeiro"], [[x, y] for x in (0, 224) for y in range(0, 1120, 224)])
        self.assertEqual(result["cosseno"], {"media": None, "minimo": None, "nan_inf": False})
        self.assertEqual(err, "")

    def test_nan_or_inf_in_either_file_fails(self):
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        for value, damaged in ((np.nan, 1), (np.inf, 0)):
            with self.subTest(value=value):
                names = [self.h5_blob(GRID, embeddings), self.h5_blob(GRID, embeddings)]
                with h5py.File(self.blobs[f"slide-h5/{names[damaged]}"], "r+") as f:
                    f["embeddings"][7, 100] = value
                code, result, _, _ = self.compare(*names)
                self.assertEqual((code, result["veredito"]), (1, "FALHA"))
                self.assertEqual(result["cosseno"], {"media": None, "minimo": None, "nan_inf": True})


class WorkDirectory(Tool):
    def setUp(self):
        super().setUp()
        embeddings = self.rng.normal(size=(50, 1024)).astype(np.float32)
        self.names = [self.h5_blob(GRID, embeddings), self.h5_blob(GRID, embeddings)]
        self.total = sum(os.path.getsize(path) for path in self.blobs.values())

    def assert_refused_before_downloading(self, code, err, azure):
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("FALHA"), err)
        self.assertEqual([method for method, _ in azure.requests], ["HEAD", "HEAD"])
        self.assertEqual(os.listdir(self.work), [])

    def test_blobs_over_the_cap_are_refused_before_any_download(self):
        with mock.patch.object(aceite_worker, "MAX_WORK_BYTES", self.total):
            self.assertEqual(self.compare(*self.names)[0], 0)
        with mock.patch.object(aceite_worker, "MAX_WORK_BYTES", self.total - 1):
            code, _, err, azure = self.compare(*self.names)
        self.assert_refused_before_downloading(code, err, azure)

    def test_too_little_free_disk_is_refused_before_any_download(self):
        def free(n):
            return mock.patch("shutil.disk_usage", return_value=Usage(10**12, 10**12 - n, n))

        with mock.patch.object(aceite_worker, "FREE_MARGIN", 1000):
            with free(self.total + 1000):
                self.assertEqual(self.compare(*self.names)[0], 0)
            with free(self.total + 999):
                code, _, err, azure = self.compare(*self.names)
        self.assert_refused_before_downloading(code, err, azure)

    def test_a_download_that_fails_leaves_the_work_directory_empty(self):
        second = f"slide-h5/{self.names[1]}"
        azure = Azure(self.blobs, broken={second: urllib.error.URLError("conexão perdida")})
        code, _, err, _ = self.compare(*self.names, azure=azure)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("FALHA"), err)
        self.assertEqual(len(azure.files_at_failure), 1)  # the first .h5 was already there
        self.assertEqual(os.listdir(self.work), [])

    def test_an_unexpected_error_still_empties_the_work_directory(self):
        azure = Azure(self.blobs, broken={f"slide-h5/{self.names[1]}": RuntimeError("defeito")})
        with self.assertRaises(RuntimeError):
            self.compare(*self.names, azure=azure)
        self.assertEqual(len(azure.files_at_failure), 1)
        self.assertEqual(os.listdir(self.work), [])

    def test_an_h5_that_arrives_different_from_its_stored_md5_is_refused(self):
        second = f"slide-h5/{self.names[1]}"
        with h5py.File(self.blobs[second], "r") as f:
            # A bit of the first embedding: the file still opens, and the change alone would pass.
            offset = f["embeddings"].id.get_offset()
        code, result, err, _ = self.compare(*self.names, azure=Azure(self.blobs, damaged={second: offset}))
        self.assertEqual((code, result), (1, None))
        self.assertTrue(err.startswith("FALHA"), err)
        self.assertEqual(os.listdir(self.work), [])

    def test_leftovers_in_the_work_directory_are_refused_and_kept(self):
        with open(os.path.join(self.work, "sobra"), "wb") as f:
            f.write(b"de uma execucao interrompida")
        code, _, err, azure = self.compare(*self.names)
        self.assertEqual(code, 1)
        self.assertTrue(err.startswith("FALHA"), err)
        self.assertEqual(azure.requests, [])
        self.assertEqual(os.listdir(self.work), ["sobra"])


class Grid(Tool):
    def setUp(self):
        super().setUp()
        self.svs = tissue_box_slide(os.path.join(self.dir.name, "lamina.svs"))
        with open(self.svs, "rb") as f:
            self.sha256 = hashlib.sha256(f.read()).hexdigest()
        self.blobs[f"wsi-publico/{SLIDE}.svs"] = self.svs
        os.makedirs(os.path.join(self.dir.name, "saida"))
        self.png = os.path.join(self.dir.name, "saida", f"{SLIDE}.png")

    def worker_h5(self, wsi_sha256):
        """The worker's first pass over the slide, written as its .h5; its blob name."""
        scratch = os.path.join(self.dir.name, "passagem")
        os.makedirs(scratch)
        tiles = passagem.first_pass(self.svs, "biopsia", scratch, workers=1)
        name = f"{TENANT}/{SLIDE}/{HASH}/{uuid.uuid4()}.h5"
        path = os.path.join(self.dir.name, "lamina.h5")
        embeddings = np.ones((len(tiles.coordinates), 1024), dtype=np.float32)
        h5.write(path, embeddings, tiles, attrs(wsi_sha256=wsi_sha256))
        self.blobs[f"slide-h5/{name}"] = path
        return name

    def grid(self, name, sha256, azure=None):
        code, out, err, azure = self.run_tool("grade", "--h5", name, "--lamina", f"wsi-publico/{SLIDE}.svs",
                                              "--sha256", sha256, "--saida", self.png, azure=azure)
        return code, (json.loads(out) if out else None), err, azure

    def test_the_grid_covers_the_tissue_and_never_the_glass(self):
        code, result, _, _ = self.grid(self.worker_h5(self.sha256), self.sha256)
        self.assertEqual(code, 0)
        self.assertEqual((result["patches"], result["lado_nivel0"]), (24, 224))
        png = np.asarray(Image.open(self.png).convert("RGB"))
        # 4096 px on the long side, drawn at 2048: half the level-0 scale.
        self.assertEqual(png.shape, (1024, 2048, 3))
        self.assertEqual(result["png_dimensoes"], [2048, 1024])
        # At half scale the tissue spans x 448 to 1120 and y 224 to 672, with 3 px of margin for the
        # resampling at its edge: no square on the glass, and no tissue pixel left without one.
        glass = np.ones(png.shape[:2], dtype=bool)
        glass[224 - 3:672 + 3, 448 - 3:1120 + 3] = False
        self.assertTrue((png[glass] == 240).all())
        tissue = png[224 + 3:672 - 3, 448 + 3:1120 - 3]
        self.assertFalse((tissue == PINK).all(axis=-1).any())
        self.assertEqual(os.listdir(self.work), [])

    def assert_refused_without_png(self, code, result, err):
        self.assertEqual((code, result), (1, None))
        self.assertTrue(err.startswith("FALHA"), err)
        self.assertFalse(os.path.exists(self.png))
        self.assertEqual(os.listdir(self.work), [])

    def test_a_wsi_other_than_the_registered_one_is_refused(self):
        # The .h5 and the operator name the same sha256; the stored WSI, consistent with its own MD5, is another.
        code, result, err, _ = self.grid(self.worker_h5("b" * 64), "b" * 64)
        self.assert_refused_without_png(code, result, err)

    def test_an_h5_of_another_wsi_is_refused_before_the_wsi_download(self):
        code, result, err, azure = self.grid(self.worker_h5("b" * 64), self.sha256)
        self.assert_refused_without_png(code, result, err)
        self.assertNotIn(("GET", f"wsi-publico/{SLIDE}.svs"), azure.requests)

    def test_a_slide_the_workers_reader_refuses_ends_in_falha(self):
        sinteticas.write_svs(self.svs, sinteticas.tissue_image(), description="generic tiff")
        with open(self.svs, "rb") as f:
            sha256 = hashlib.sha256(f.read()).hexdigest()
        name = self.h5_blob(GRID, np.ones((50, 1024), dtype=np.float32), wsi_sha256=sha256)
        code, result, err, _ = self.grid(name, sha256)
        self.assert_refused_without_png(code, result, err)


class Arguments(Tool):
    def setUp(self):
        super().setUp()
        self.name = self.h5_blob(GRID, self.rng.normal(size=(50, 1024)).astype(np.float32))
        self.azure = Azure(self.blobs)

    def test_comparar_needs_two_different_h5(self):
        for argv in (["--h5", self.name], ["--h5", self.name, "--h5", self.name]):
            with self.subTest(names=len(argv) // 2):
                code, _, err, _ = self.run_tool("comparar", *argv, azure=self.azure)
                self.assertEqual(code, 1)
                self.assertTrue(err.startswith("FALHA"), err)
        self.assertEqual(self.azure.requests, [])

    def test_names_off_the_contract_are_refused_before_any_request(self):
        for other in (self.name.removesuffix(".h5") + ".qc.h5", "../" + self.name):
            with self.subTest(other=other):
                with self.assertRaises(SystemExit) as caught:
                    self.run_tool("comparar", "--h5", self.name, "--h5", other, azure=self.azure)
                self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.azure.requests, [])

    def test_grade_needs_a_wsi_blob_and_a_sha256_of_the_contract(self):
        cases = ((f"wsi-publico/../{SLIDE}.svs", "a" * 64), (f"slide-h5/{SLIDE}.svs", "a" * 64),
                 (f"wsi-publico/{SLIDE}.svs", "A" * 64), (f"wsi-publico/{SLIDE}.svs", "a" * 63))
        for lamina, sha256 in cases:
            with self.subTest(lamina=lamina, sha256=f"{sha256[0]} x {len(sha256)}"):
                with self.assertRaises(SystemExit) as caught:
                    self.run_tool("grade", "--h5", self.name, "--lamina", lamina, "--sha256", sha256,
                                  "--saida", os.path.join(self.dir.name, "grade.png"), azure=self.azure)
                self.assertEqual(caught.exception.code, 2)
        self.assertEqual(self.azure.requests, [])


class ProductionImage(unittest.TestCase):
    def test_the_tool_imports_without_tifffile(self):
        # Only the tests need tifffile; the worker image on VM2 has none.
        code = "import sys; sys.modules['tifffile'] = None; import aceite_worker"
        result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_as_a_script_a_refusal_exits_with_1(self):
        # As the operator runs it; the repeated name is refused before any request.
        name = f"{TENANT}/{SLIDE}/{HASH}/{uuid.uuid4()}.h5"
        result = subprocess.run([sys.executable, aceite_worker.__file__, "comparar", "--h5", name, "--h5", name],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(result.stderr.startswith("FALHA"), result.stderr)


if __name__ == "__main__":
    unittest.main()
