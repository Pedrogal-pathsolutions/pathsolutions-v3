import os
import tempfile
import unittest
from unittest import mock

import numpy as np

import sinteticas
from pathsol_worker import slide as slides


class OpenSlide(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def svs(self, name="l.svs", **kwargs):
        path = os.path.join(self.dir.name, name)
        sinteticas.write_svs(path, kwargs.pop("image", sinteticas.tissue_image()), **kwargs)
        return path

    def refused(self, path):
        with self.assertRaises(slides.UnsupportedFormat) as caught:
            slides.open_slide(path)
        return caught.exception.reason

    def test_opens_an_aperio_pyramid(self):
        with slides.open_slide(self.svs()) as s:
            self.assertEqual(s.dimensions, (2048, 1024))
            self.assertEqual(s.level_count, 2)
            self.assertAlmostEqual(s.mpp, 0.25)
            self.assertEqual(s.mpp_source, "openslide.mpp-x/mpp-y")
            self.assertRegex(s.reader, r"^openslide \d+\.\d+\.\d+ \(openslide-python \d+\.\d+\.\d+\)$")

    def test_only_allowlisted_properties_leave_the_reader(self):
        path = self.svs(extra="|Filename = caso-12345|User = fulano|Barcode = 98765")
        with slides.open_slide(path) as s:
            self.assertFalse(hasattr(s, "properties"))
            self.assertFalse(hasattr(s, "associated_images"))
            seen = repr(vars(s)) + repr(s)
            for secret in ("caso-12345", "fulano", "98765", "Aperio Image Library"):
                self.assertNotIn(secret, seen)

    def test_refuses_other_extensions(self):
        path = self.svs(name="l.tif")
        self.assertEqual(self.refused(path), "formato não suportado")

    def test_refuses_a_file_that_is_not_aperio(self):
        path = self.svs(description="generic tiff")
        self.assertEqual(self.refused(path), "formato não suportado")

    def test_refuses_garbage(self):
        path = os.path.join(self.dir.name, "lixo.svs")
        with open(path, "wb") as f:
            f.write(os.urandom(4096))
        self.assertEqual(self.refused(path), "formato não suportado")

    def test_refuses_a_slide_without_pyramid(self):
        self.assertEqual(self.refused(self.svs(downsamples=(1,))), "formato não suportado")

    def test_scale_out_of_range_or_missing_is_unavailable(self):
        for mpp in (0.9, 0.05, None):
            with self.subTest(mpp=mpp):
                path = self.svs(name=f"l{mpp}.svs", mpp=mpp)
                self.assertEqual(self.refused(path), "escala indisponível")

    def test_scale_inside_the_range(self):
        for mpp in (0.1, 0.52, 0.55):
            with self.subTest(mpp=mpp), slides.open_slide(self.svs(name=f"l{mpp}.svs", mpp=mpp)) as s:
                self.assertAlmostEqual(s.mpp, mpp)


class Mpp(unittest.TestCase):
    def test_x_and_y_must_agree_within_one_percent(self):
        self.assertAlmostEqual(slides.checked_mpp("0.25", "0.2524"), 0.2512)
        with self.assertRaises(slides.UnsupportedFormat):
            slides.checked_mpp("0.25", "0.2530")

    def test_unreadable_values(self):
        for x, y in ((None, "0.25"), ("abc", "0.25"), ("nan", "nan"), ("inf", "inf")):
            with self.subTest(x=x, y=y), self.assertRaises(slides.UnsupportedFormat):
                slides.checked_mpp(x, y)


class Reading(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "l.svs")
        sinteticas.write_svs(self.path, sinteticas.tissue_image())

    def test_patch_is_224_rgb_of_the_level0_square(self):
        with slides.open_slide(self.path) as s:
            tissue = np.asarray(s.read_patch(0, 0, 448))
            glass = np.asarray(s.read_patch(1344, 0, 448))
        self.assertEqual(tissue.shape, (224, 224, 3))
        np.testing.assert_allclose(tissue.reshape(-1, 3).mean(axis=0), (200, 120, 170), atol=1)
        np.testing.assert_allclose(glass.reshape(-1, 3).mean(axis=0), (240, 240, 240), atol=1)

    def test_area_outside_the_scan_reads_as_white_glass(self):
        with slides.open_slide(self.path) as s:
            patch = np.asarray(s.read_patch(1900, 900, 448))
        self.assertTrue((patch[-50:, -50:] == 255).all())

    def test_thumbnail_near_the_requested_scale(self):
        with slides.open_slide(self.path) as s:
            thumb, downsample = s.thumbnail(4.0)
        # 4 um/px at 0.25 um/px is 16x; the 4x level is read and reduced.
        self.assertEqual(thumb.shape, (64, 128, 3))
        self.assertAlmostEqual(downsample, 16.0)

    def test_thumbnail_refuses_when_no_level_is_small_enough(self):
        with slides.open_slide(self.path) as s, mock.patch.object(slides, "MAX_THUMBNAIL_SOURCE_PIXELS", 1000):
            with self.assertRaises(slides.UnsupportedFormat):
                s.thumbnail(4.0)


class ThumbnailLevel(unittest.TestCase):
    """Real 40x scans state mpp a bit above 0.25, so 4 um/px asks for a little
    under 16x; the 16x level must still be used, not the 4x one (benchmark of 30/10)."""

    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def level_read(self, mpp, downsamples, cap):
        path = os.path.join(self.dir.name, f"l{mpp}{len(downsamples)}.svs")
        sinteticas.write_svs(path, sinteticas.tissue_image(4096, 2048), mpp=mpp, downsamples=downsamples)
        with slides.open_slide(path) as s, mock.patch.object(slides, "MAX_THUMBNAIL_SOURCE_PIXELS", cap):
            with mock.patch.object(s._handle, "read_region", wraps=s._handle.read_region) as read:
                thumb, downsample = s.thumbnail(4.0)
        return read.call_args.args[1], thumb.shape, downsample

    def test_level_slightly_coarser_than_the_target_is_used(self):
        level, shape, downsample = self.level_read(0.2525, (1, 4, 16), cap=10**9)
        self.assertEqual(level, 2)
        self.assertEqual(shape, (129, 259, 3))
        self.assertAlmostEqual(downsample, 4096 / 259)

    def test_coarser_level_when_the_finer_ones_exceed_the_cap(self):
        # 20x scan: 0.5, 2 and 8 um/px; only the 8 um/px level fits.
        level, shape, _ = self.level_read(0.5, (1, 4, 16), cap=50_000)
        self.assertEqual(level, 2)
        self.assertEqual(shape, (256, 512, 3))

    def test_refuses_a_pyramid_without_a_level_up_to_twice_the_target(self):
        with self.assertRaises(slides.UnsupportedFormat):
            self.level_read(0.25, (1, 64), cap=1_000_000)


if __name__ == "__main__":
    unittest.main()
