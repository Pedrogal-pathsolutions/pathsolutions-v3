import unittest

import cv2
import numpy as np

from pathsol_worker import qc

PINK = (200, 120, 170)
GLASS = (240, 240, 240)


def checkerboard(size=224, cell=4, a=PINK, b=(120, 40, 100)):
    yy, xx = np.indices((size, size))
    on = ((yy // cell + xx // cell) % 2).astype(bool)
    image = np.empty((size, size, 3), dtype=np.uint8)
    image[on], image[~on] = a, b
    return image


class Threshold(unittest.TestCase):
    def test_separates_tissue_from_glass(self):
        thumb = np.full((128, 256, 3), GLASS, dtype=np.uint8)
        thumb[:, :128] = PINK
        threshold = qc.tissue_threshold(thumb)
        mask = qc.tissue_mask(thumb, threshold)
        self.assertTrue(mask[:64, :128].all())
        self.assertFalse(mask[:64, 140:240].any())

    def test_blank_glass_has_no_tissue(self):
        rng = np.random.default_rng(0)
        glass = np.clip(240 + rng.integers(-3, 4, (128, 256, 3)), 0, 255).astype(np.uint8)
        threshold = qc.tissue_threshold(glass)
        self.assertGreaterEqual(threshold, qc.MIN_SATURATION)
        self.assertFalse(qc.tissue_mask(glass, threshold).any())


class PatchMetrics(unittest.TestCase):
    def test_tissue_fraction(self):
        patch = np.full((224, 224, 3), GLASS, dtype=np.uint8)
        patch[:, :112] = PINK
        fraction, _, _ = qc.patch_metrics(patch, threshold=30)
        self.assertAlmostEqual(fraction, 0.5, places=2)

    def test_blur_lowers_both_focus_metrics(self):
        sharp = checkerboard()
        blurred = cv2.GaussianBlur(sharp, (0, 0), 3)
        _, lap_sharp, ten_sharp = qc.patch_metrics(sharp, threshold=30)
        _, lap_blur, ten_blur = qc.patch_metrics(blurred, threshold=30)
        self.assertLess(lap_blur, lap_sharp / 10)
        self.assertLess(ten_blur, ten_sharp / 10)

    def test_focus_only_counts_tissue_pixels(self):
        # Sharp edges on glass must not make a smooth tissue patch look sharp.
        patch = np.full((224, 224, 3), PINK, dtype=np.uint8)
        patch[:, 112:] = checkerboard(a=(255, 255, 255), b=(200, 200, 200))[:, 112:]
        _, lap, ten = qc.patch_metrics(patch, threshold=30)
        self.assertLess(lap, 1.0)
        self.assertLess(ten, 1.0)

    def test_no_tissue_gives_zero_focus(self):
        glass = np.full((224, 224, 3), GLASS, dtype=np.uint8)
        self.assertEqual(qc.patch_metrics(glass, threshold=30), (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
