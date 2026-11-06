"""The synthetic slide of empty glass for test 5 of the worker, on a small instance, and the default one's size.

Runs in the worker test image, with the worker's code from the repository ahead of the installed one:

    docker run --rm --network none -v "$PWD/services/worker/src:/worker:ro" -v "$PWD/deploy/vm1/aceite:/aceite:ro" \
        -e PYTHONPATH=/worker:/aceite pathsol-worker-teste:<tag> unittest discover -s /aceite -p 'test_lamina_sem_tecido.py'
"""
import contextlib
import errno
import io
import os
import shutil
import tempfile
import unittest
import uuid
from unittest import mock

import desidentificar

try:
    import numpy as np
    import openslide
    import tifffile
    from pathsol_worker import banco, consumidor, processo, qc
    from pathsol_worker import slide as slides
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste do worker, com services/worker/src no PYTHONPATH") from None

import lamina_sem_tecido

SMALL_MM = (1, 0.5)  # 4000 x 2000 pixels at 0.25 um/px
# The default slide, 3 x 2 mm, has about 135 MiB; it must stay well below 1 GiB.
MAX_DEFAULT_BYTES = 256 * 1024**2


class Staged:
    """The Blob as the worker sees it: the WSI it downloads is the file at path, and nothing may be uploaded."""

    def __init__(self, path):
        self.path = path

    def download(self, container, name, target, sha256):
        shutil.copyfile(self.path, target)

    def upload(self, name, path, md5):
        raise AssertionError("o worker enviou um arquivo ao Blob")


class NoGpu:
    def embed(self, patches):
        raise AssertionError("o worker usou o Hibou-L")


def recorded(path, material, workroot):
    """The outcome the worker writes to the database for the slide at path."""
    job = banco.Job(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "wsi-publico", "lamina.svs", "0" * 64, None, material,
                    "HE", "RUNNING", 0)
    return processo.Processor(Staged(path), NoGpu(), "{}", {}, workroot, workers=1)(job)


class SmallSlide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(work.cleanup)
        cls.work = work.name
        cls.path = lamina_sem_tecido.stage(work.name, SMALL_MM)

    def test_the_worker_reader_opens_it_at_40x(self):
        with slides.open_slide(self.path) as s:
            self.assertEqual(s.dimensions, (4000, 2000))
            self.assertEqual(s.mpp, 0.25)
            self.assertEqual(s.level_downsamples, (1.0, 4.0, 16.0))
        with openslide.OpenSlide(self.path) as s:
            self.assertEqual(s.properties[openslide.PROPERTY_NAME_OBJECTIVE_POWER], "40")
            self.assertEqual(set(s.associated_images), {"thumbnail"})  # no label, no macro

    def test_qc1_takes_its_thumbnail_from_the_4_um_level(self):
        with slides.open_slide(self.path) as s, \
                mock.patch.object(s._handle, "read_region", wraps=s._handle.read_region) as read:
            thumb, downsample = s.thumbnail(qc.QC1_MPP)
        self.assertEqual(read.call_args.args[1], 2)
        self.assertEqual(downsample, 16)
        self.assertLess(qc.saturation(thumb).max(), qc.MIN_SATURATION)

    def test_glass_is_near_white_with_noise_and_a_slight_shading(self):
        level0 = tifffile.imread(self.path, key=0)
        corner, opposite = level0[:256, :256], level0[-256:, -256:]
        for region in (corner, opposite):
            for channel in np.moveaxis(region, -1, 0):
                self.assertTrue(230 < channel.mean() < 250, f"média {channel.mean():.2f}")
                self.assertTrue(1 < channel.std() < 3, f"ruído {channel.std():.2f}")
        shading = corner.mean() - opposite.mean()
        self.assertTrue(2 < shading < 10, f"sombreamento {shading:.2f}")

    def test_the_worker_records_empty_glass_without_the_gpu(self):
        for material in ("biopsia", "peca", "citologia"):
            with self.subTest(material=material):
                outcome = recorded(self.path, material, tempfile.mkdtemp(dir=self.work))
                self.assertEqual(outcome, consumidor.QcFailed("empty_glass"))
                self.assertEqual(outcome.state, "QC_FAILED")

    def test_the_deidentified_copy_is_still_empty_glass(self):
        copy = os.path.join(self.work, "copia.svs")
        self.assertEqual(desidentificar.deidentify(self.path, copy), 0)  # no label or macro to remove
        outcome = recorded(copy, "biopsia", tempfile.mkdtemp(dir=self.work))
        self.assertEqual(outcome, consumidor.QcFailed("empty_glass"))


class Writing(unittest.TestCase):
    def setUp(self):
        work = tempfile.TemporaryDirectory()
        self.addCleanup(work.cleanup)
        self.dir = work.name

    def run_main(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            code = lamina_sem_tecido.main(self.dir)
        return code, output.getvalue()

    def test_the_default_slide_takes_a_fresh_uuid_name_and_stays_under_the_bound(self):
        code, output = self.run_main()
        self.assertEqual(code, 0)
        (name,) = os.listdir(self.dir)  # and no partial file
        self.assertRegex(name, r"^[0-9a-f-]{36}\.svs$")
        self.assertIn(f"OK {os.path.join(self.dir, name)}", output)
        self.assertLess(os.path.getsize(os.path.join(self.dir, name)), MAX_DEFAULT_BYTES)

    def test_a_write_cut_short_leaves_nothing_in_the_directory(self):
        seen = []

        def cut_short(f, size_mm):
            seen.extend(os.listdir(self.dir))
            f.write(b"II*\0")
            raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))

        with mock.patch.object(lamina_sem_tecido, "write_svs", cut_short):
            code, output = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn("FALHA", output)
        self.assertEqual(len(seen), 1)
        self.assertRegex(seen[0], r"\.svs\.parcial$")  # a name the upload script refuses
        self.assertEqual(os.listdir(self.dir), [])

    def test_never_writes_over_an_existing_file(self):
        taken = uuid.uuid4()
        path = os.path.join(self.dir, f"{taken}.svs")
        with open(path, "wb") as f:
            f.write(b"ja existe")
        with mock.patch.object(lamina_sem_tecido.uuid, "uuid4", return_value=taken), \
                self.assertRaises(FileExistsError):
            lamina_sem_tecido.stage(self.dir, SMALL_MM)
        with open(path, "rb") as f:
            self.assertEqual(f.read(), b"ja existe")
        self.assertEqual(os.listdir(self.dir), [f"{taken}.svs"])


if __name__ == "__main__":
    unittest.main()
