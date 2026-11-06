"""Acceptance test 9 (focus) on synthetic slides, with a fake extractor: no GPU, no network, no Azure.

Runs in the worker test image built from the same commit, which has tifffile and OpenSlide:

    docker run --rm --network none -v "$PWD/deploy/vm2/aceite:/aceite:ro" -e PYTHONPATH=/aceite \
        pathsol-worker-teste:<commit> unittest discover -s /aceite -p 'test_foco.py'
"""
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from unittest import mock

try:
    import cv2
    import numpy as np
    import openslide
    import tifffile
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste do worker") from None

import foco
from pathsol_worker import blob, qc
from pathsol_worker import slide as slides

PINK = (200, 120, 170)
GLASS = 240
SIDE = 224  # a patch at 0.5 µm/px
# Crop of the tests: 20 x 20 patches, half of them tissue, above the 150 patches the focus rule needs.
CELLS = 20
VERSION = '{"extrator":"teste"}'
BLOB = "0f6c2a43-8d1e-4f57-9b8e-2b5d7c9a1e34.svs"
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def sharp_tissue(rng, height, width):
    """Pink tissue with fine texture: a high Laplacian, as in focus."""
    noise = rng.integers(-40, 41, (height, width, 1), dtype=np.int16)
    return np.clip(np.array(PINK, dtype=np.int16) + noise, 0, 255).astype(np.uint8)


def cells_tissue(period, height, width):
    """Tissue with light and dark blobs repeating every `period` pixels. Unlike fine noise, half the blur
    leaves it in focus."""
    y, x = np.mgrid[:height, :width]
    wave = 80 * np.sin(2 * np.pi * x / period) * np.sin(2 * np.pi * y / period)
    return np.clip(np.array((150, 90, 150)) + wave[..., None], 0, 255).astype(np.uint8)


def source_slide(path, rng, blurred_columns=0, tissue_columns=12.3, mpp=0.5):
    """24 x 20 patches: tissue in the columns on the left, glass on the right.

    With 12.3 columns of tissue, the crop closest to half tissue starts at
    column 2. In it, 200 patches are all tissue, and the 20 of the 13th
    column, at 30% tissue, are extracted but not counted by the focus rule.
    blurred_columns blurs that many columns of tissue from column 2, as a
    slide out of focus in part.
    """
    image = np.full((CELLS * SIDE, 24 * SIDE, 3), GLASS, dtype=np.uint8)
    width = round(tissue_columns * SIDE)
    image[:, :width] = sharp_tissue(rng, CELLS * SIDE, width)
    if blurred_columns:
        part = slice(2 * SIDE, (2 + blurred_columns) * SIDE)
        image[:, part] = cv2.GaussianBlur(image[:, part], (0, 0), 6)
    # Written here, not by foco: an Aperio-style SVS with a level at 4 µm/px for QC 1.
    with tifffile.TiffWriter(path) as tif:
        for factor in (1, 8):
            level = np.ascontiguousarray(image[::factor, ::factor])
            height, width = level.shape[:2]
            text = f"{width}x{height} [0,0 {width}x{height}] (256x256) RGB|MPP = {mpp}" if factor == 1 else f"{width}x{height}"
            tif.write(level, tile=(256, 256), photometric="rgb", compression="zlib",
                      description=f"Aperio Image Library v12.0.15\r\n{text}", metadata=None)
    return path


class FakeSource:
    """The WSI container as VM2 reads it: one blob's size, and its download checked by sha256."""

    def __init__(self, path):
        self.path = path
        self.downloads = []

    def size(self, container, name):
        return os.path.getsize(self.path)

    def download(self, container, name, path, sha256_hex):
        self.downloads.append((container, name))
        shutil.copyfile(self.path, path)
        if sha256(path) != sha256_hex:
            raise blob.BlobError("o sha256 não é o do job")


class MissingBlob(FakeSource):
    """A blob that is not in the container: the HEAD answers 404."""

    def size(self, container, name):
        raise urllib.error.HTTPError(f"https://teste/{container}/{name}", 404, "The specified blob does not exist.",
                                     None, None)


class FakeExtractor:
    """Hibou-L without the GPU; with a limit, it fails as the GPU would past that many patches."""

    def __init__(self, limit=None):
        self.patches = 0
        self.limit = limit

    def embed(self, patches):
        if self.limit is not None and self.patches + len(patches) > self.limit:
            raise RuntimeError("falha na GPU")
        self.patches += len(patches)
        return np.ones((len(patches), 1024), dtype=np.float32)


def run_main(source, root, extractor, blob_name=BLOB, sha256_hex=None):
    """foco.main with the container, Hibou-L and its versions faked: (exit code, stdout, stderr)."""
    argv = ["--modelo", "/modelo", "--trabalho", root, "--container", "wsi-publico", "--blob", blob_name,
            "--sha256", sha256_hex or sha256(source.path)]
    out, err = io.StringIO(), io.StringIO()
    with (mock.patch.object(foco, "Source", return_value=source),
          mock.patch("pathsol_worker.extractor.Extractor", return_value=extractor),
          mock.patch("pathsol_worker.versao.extractor_version", return_value=VERSION),
          mock.patch("pathsol_worker.versao.software", return_value={"torch": "teste"}),
          mock.patch.object(foco, "CROP_CELLS", CELLS),
          contextlib.redirect_stdout(out), contextlib.redirect_stderr(err)):
        try:
            code = foco.main(argv)
        except SystemExit as refused:  # argparse
            code = refused.code
    return code, out.getvalue(), err.getvalue()


class Run(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.root = os.path.join(self.dir.name, "trabalho")
        os.mkdir(self.root)

    def source(self, kind=FakeSource, **layout):
        return kind(source_slide(os.path.join(self.dir.name, "origem.svs"), np.random.default_rng(0), **layout))


class SharpSlide(unittest.TestCase):
    """One whole run on a sharp synthetic slide, as the operator runs it on VM2."""

    @classmethod
    def setUpClass(cls):
        work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(work.cleanup)
        cls.source = FakeSource(source_slide(os.path.join(work.name, "origem.svs"), np.random.default_rng(0)))
        cls.root = os.path.join(work.name, "trabalho")
        os.mkdir(cls.root)
        cls.extractor = FakeExtractor()
        cls.code, out, cls.err = run_main(cls.source, cls.root, cls.extractor)
        cls.report = json.loads(out)
        cls.copies = {copy["copia"]: copy for copy in cls.report["copias"]}

    def test_the_crop_holds_tissue_and_glass_on_the_worker_grid(self):
        self.assertEqual(self.report["recorte"]["origem"], [2 * SIDE, 0])
        self.assertEqual(self.report["recorte"]["lado_px"], CELLS * SIDE)

    def test_the_blurred_fraction_lands_as_planned(self):
        # A fraction of the 200 patches the focus rule counts; the 20 extracted at 30% tissue are never blurred.
        for name, planned, blurred in (("original", 0.0, 0), ("abaixo", 0.10, 20), ("acima", 0.40, 80)):
            with self.subTest(copia=name):
                copy = self.copies[name]
                self.assertEqual(copy["fracao_planejada"], planned)
                self.assertEqual(copy["patches_extraidos"], 220)
                self.assertEqual(copy["patches_do_foco"], 200)
                self.assertEqual(copy["patches_borrados"], blurred)
                self.assertAlmostEqual(copy["fracao_fora_de_foco"], planned)

    def test_the_copy_above_a_fifth_ends_qc_failed_focus_with_its_scores_and_no_h5(self):
        copy = self.copies["acima"]
        self.assertEqual(copy["resultado"], "QC_FAILED focus")
        self.assertEqual(len(copy["arquivos"]), 1)
        self.assertRegex(copy["arquivos"][0], rf"^{UUID}/{UUID}/[0-9a-f]{{12}}/{UUID}\.qc\.h5$")
        self.assertTrue(copy["confere"])

    def test_the_original_and_the_copy_below_a_fifth_go_on_to_extraction(self):
        for name in ("original", "abaixo"):
            with self.subTest(copia=name):
                copy = self.copies[name]
                self.assertEqual(copy["resultado"], "COMPLETED")
                self.assertEqual(len(copy["arquivos"]), 1)
                self.assertRegex(copy["arquivos"][0], rf"^{UUID}/{UUID}/[0-9a-f]{{12}}/{UUID}\.h5$")
                self.assertTrue(copy["confere"])
        # 220 patches in each; the copy blocked by focus never reaches the GPU.
        self.assertEqual(self.extractor.patches, 440)

    def test_all_three_as_expected_give_the_verdict_ok_and_exit_code_zero(self):
        self.assertEqual(self.report["veredito"], "OK")
        self.assertEqual(self.code, 0)

    def test_the_slide_comes_once_from_its_container_and_the_work_directory_is_emptied(self):
        self.assertEqual(self.source.downloads, [("wsi-publico", BLOB)])
        self.assertEqual(os.listdir(self.root), [])


class Arguments(Run):
    def test_a_blob_not_named_by_its_uuid_is_refused_and_never_printed(self):
        source = self.source()
        code, out, err = run_main(source, self.root, FakeExtractor(), blob_name="caso-123.svs")
        self.assertEqual(code, 2)
        self.assertNotIn("caso-123", out + err)
        self.assertEqual(source.downloads, [])


class Ceiling(Run):
    def test_a_step_that_would_pass_the_ceiling_is_refused_before_it_writes(self):
        source = self.source()
        size = os.path.getsize(source.path)
        # Below the slide: refused before the download. Above the slide but below one copy with its job
        # (3 x 60 MB of pixels and 400 patches of 147 KiB): refused before the first copy.
        for ceiling, downloads in ((size - 1, []), (size + 1024**2, [("wsi-publico", BLOB)])):
            with self.subTest(teto=ceiling):
                source.downloads.clear()
                extractor = FakeExtractor()
                with mock.patch.object(foco, "MAX_WORK_BYTES", ceiling):
                    code, out, err = run_main(source, self.root, extractor)
                self.assertEqual((code, out), (1, ""))
                self.assertRegex(err, r"(?m)^FALHA: .*teto")
                self.assertEqual(source.downloads, downloads)
                self.assertEqual(extractor.patches, 0)
                self.assertEqual(os.listdir(self.root), [])


class Root(Run):
    def test_a_work_root_with_anything_in_it_is_refused_and_left_as_it_was(self):
        # Left by a run that was killed, or by hand: the tool removes only what it created.
        with open(os.path.join(self.root, "outro"), "w") as f:
            f.write("de outra execução")
        source = self.source()
        code, out, err = run_main(source, self.root, FakeExtractor())
        self.assertEqual((code, out), (1, ""))
        self.assertRegex(err, r"(?m)^FALHA: .*vazio")
        self.assertEqual(source.downloads, [])
        self.assertEqual(os.listdir(self.root), ["outro"])


class OperatorFailures(Run):
    """What the operator can fix ends in one FALHA line, with no traceback, and the work directory goes."""

    def assert_one_falha_line(self, source, pattern, **kwargs):
        code, out, err = run_main(source, self.root, FakeExtractor(), **kwargs)
        self.assertEqual((code, out), (1, ""))
        self.assertRegex(err, rf"\AFALHA: [^\n]*{pattern}[^\n]*\n\Z")
        self.assertEqual(os.listdir(self.root), [])

    def test_a_slide_with_another_sha256(self):
        self.assert_one_falha_line(self.source(), "sha256", sha256_hex="0" * 64)

    def test_a_blob_missing_from_the_container(self):
        self.assert_one_falha_line(self.source(MissingBlob), "404")

    def test_a_slide_the_worker_refuses(self):
        self.assert_one_falha_line(self.source(mpp=0.9), "escala indisponível")


class Failure(Run):
    def test_the_work_directory_goes_even_when_a_job_fails(self):
        # The GPU fails in the second copy, with the first copy's .h5 already in the work directory.
        with self.assertRaisesRegex(RuntimeError, "falha na GPU"):
            run_main(self.source(), self.root, FakeExtractor(limit=300))
        self.assertEqual(os.listdir(self.root), [])


class TooLittleTissue(Run):
    def test_a_crop_the_focus_rule_cannot_block_is_refused(self):
        # 3 columns of tissue give the rule 60 patches, only glass gives it none: it blocks only from 150.
        for columns in (3, 0):
            with self.subTest(colunas=columns):
                code, out, err = run_main(self.source(tissue_columns=columns), self.root, FakeExtractor())
                self.assertEqual((code, out), (1, ""))
                self.assertRegex(err, r"(?m)^FALHA: .*150")
                self.assertEqual(os.listdir(self.root), [])


class Verdict(Run):
    def test_a_slide_out_of_focus_in_part_fails_the_verdict_and_the_exit_code(self):
        # 3 of the crop's 10 columns of whole tissue already blurred: the original is blocked, not extracted.
        code, out, _ = run_main(self.source(blurred_columns=3), self.root, FakeExtractor())
        report = json.loads(out)
        original = report["copias"][0]
        self.assertEqual((original["copia"], original["resultado"]), ("original", "QC_FAILED focus"))
        self.assertAlmostEqual(original["fracao_fora_de_foco"], 0.30)
        self.assertFalse(original["confere"])
        self.assertEqual(report["veredito"], "FALHA")
        self.assertEqual(code, 1)

    def test_a_copy_with_the_expected_state_but_without_its_scores_file_fails_the_verdict(self):
        class LosesScores(foco.LocalBlob):
            """A worker that ends a focus block without the scores file."""

            def upload(self, name, path, md5):
                if not name.endswith(".qc.h5"):
                    super().upload(name, path, md5)

        with mock.patch.object(foco, "LocalBlob", LosesScores):
            code, out, _ = run_main(self.source(), self.root, FakeExtractor())
        report = json.loads(out)
        above = report["copias"][2]
        self.assertEqual((above["copia"], above["resultado"], above["arquivos"]), ("acima", "QC_FAILED focus", []))
        self.assertIsNone(above["fracao_fora_de_foco"])
        self.assertFalse(above["confere"])
        self.assertEqual((report["veredito"], code), ("FALHA", 1))


class Imports(unittest.TestCase):
    def test_the_script_imports_no_torch_so_neither_do_the_qc2_processes_it_spawns(self):
        # A spawned process runs the script's top level again as its main module.
        probe = "import sys, foco; print('torch' in sys.modules)"
        result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout.strip(), "False")


class SvsCopy(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def test_the_worker_reads_the_copy_with_its_scale_its_pixels_and_a_level_for_qc1(self):
        image = sharp_tissue(np.random.default_rng(0), 768, 1024)
        for mpp, factor in ((0.5, 8), (0.499, 8), (0.25, 16)):
            with self.subTest(mpp=mpp):
                path = os.path.join(self.dir.name, f"{mpp}.svs")
                foco.write_svs(path, image, mpp)
                with slides.open_slide(path) as s:
                    self.assertEqual(s.mpp, mpp)
                    self.assertEqual(s.level_dimensions, ((1024, 768), (1024 // factor, 768 // factor)))
                    thumbnail, _ = s.thumbnail(qc.QC1_MPP)
                self.assertEqual(thumbnail.shape[2], 3)
                with openslide.OpenSlide(path) as handle:
                    level0 = np.asarray(handle.read_region((0, 0), 0, (1024, 768)).convert("RGB"))
                np.testing.assert_array_equal(level0, image)


class Blur(unittest.TestCase):
    def test_only_the_chosen_cells_are_blurred_from_their_real_surroundings(self):
        crop = sharp_tissue(np.random.default_rng(1), 128, 128)  # 4 x 4 cells of 32 px
        before = crop.copy()
        chosen = {(32, 0), (64, 64)}
        out = foco.blurred(crop, sorted(chosen), 32, 2.0)
        reference = cv2.GaussianBlur(crop, (0, 0), 2.0)
        np.testing.assert_array_equal(crop, before)
        for y in range(0, 128, 32):
            for x in range(0, 128, 32):
                expected = reference if (x, y) in chosen else crop
                np.testing.assert_array_equal(out[y : y + 32, x : x + 32], expected[y : y + 32, x : x + 32])

    def test_the_blur_is_strong_for_the_worker_at_any_mpp(self):
        # Blobs every 10 µm, about the size of cells; at 0.25 µm/px, half the blur leaves the cell in focus.
        with tempfile.TemporaryDirectory() as tmp:
            for mpp in (0.5, 0.25):
                with self.subTest(mpp=mpp):
                    side = round(SIDE * 0.5 / mpp)
                    crop = cells_tissue(10 / mpp, side, 2 * side)
                    path = os.path.join(tmp, f"{mpp}.svs")
                    foco.write_svs(path, foco.blurred(crop, [(side, 0)], side, foco.blur_sigma(mpp)), mpp)
                    with slides.open_slide(path) as s:
                        sharp, blurred = (np.asarray(s.read_patch(x, 0, side)) for x in (0, side))
                    _, sharp_laplacian, _ = qc.patch_metrics(sharp, qc.MIN_SATURATION)
                    _, blurred_laplacian, _ = qc.patch_metrics(blurred, qc.MIN_SATURATION)
                    # The worker's cut for a patch out of focus, with the sharp cell as the slide's P90.
                    self.assertLess(blurred_laplacian, qc.FOCUS_RELATIVE * sharp_laplacian)


class LocalBlob(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.copies = os.path.join(self.dir.name, "copias")
        os.mkdir(self.copies)
        with open(os.path.join(self.copies, "c.svs"), "wb") as f:
            f.write(b"copia")
        self.local = foco.LocalBlob(self.copies, os.path.join(self.dir.name, "slide-h5"))

    def test_download_checks_the_sha256(self):
        target = os.path.join(self.dir.name, "baixada.svs")
        good = "5dd1ff6d2de3531d47771c8cff57be3e57835b319b3bec166b29b6f1fdcda31f"  # sha256 of b"copia"
        self.local.download("local", "c.svs", target, good)
        with open(target, "rb") as f:
            self.assertEqual(f.read(), b"copia")
        with self.assertRaises(blob.BlobError):
            self.local.download("local", "c.svs", target, "0" * 64)

    def test_upload_writes_in_the_work_directory_and_keeps_the_name(self):
        path = os.path.join(self.dir.name, "x.h5")
        with open(path, "wb") as f:
            f.write(b"h5")
        self.local.upload("t/s/v/j.h5", path, b"md5")
        with open(os.path.join(self.dir.name, "slide-h5", "t", "s", "v", "j.h5"), "rb") as f:
            self.assertEqual(f.read(), b"h5")
        self.assertEqual(self.local.written, ["t/s/v/j.h5"])


if __name__ == "__main__":
    unittest.main()
