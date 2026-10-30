import os
import tempfile
import unittest

import numpy as np

import sinteticas
from pathsol_worker import grid, patches, qc
from pathsol_worker import slide as slides


class Candidates(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "l.svs")
        sinteticas.write_svs(self.path, sinteticas.tissue_image())

    def test_thumbnail_mask_finds_the_tissue_block(self):
        with slides.open_slide(self.path) as s:
            mask, downsample, threshold, area = qc.thumbnail_mask(s)
        self.assertEqual(downsample, 16.0)
        self.assertGreaterEqual(threshold, qc.MIN_SATURATION)
        self.assertTrue(mask[:40, :60].all())
        self.assertFalse(mask[:40, 70:110].any())

    def test_candidates_are_the_cells_touching_tissue(self):
        mask = np.zeros((64, 128), dtype=bool)
        mask[:, :64] = True  # level-0 x below 1024 at downsample 16
        side, coords = grid.candidates((2048, 1024), 0.25, mask, 16.0)
        self.assertEqual(side, 448)
        self.assertEqual({int(x) for x, _ in coords}, {0, 448, 896})
        self.assertEqual({int(y) for _, y in coords}, {0, 448})

    def test_patches_come_in_order_with_their_metrics(self):
        coords = np.array([[0, 0], [1344, 0], [448, 448], [0, 448]], dtype=np.int32)
        one = list(patches.read_patches(self.path, coords, 448, threshold=30, workers=1))
        two = list(patches.read_patches(self.path, coords, 448, threshold=30, workers=2))
        self.assertEqual(len(one), 4)
        for (p1, m1), (p2, m2) in zip(one, two):
            np.testing.assert_array_equal(p1, p2)
            self.assertEqual(m1, m2)
        self.assertEqual(one[0][0].shape, (224, 224, 3))
        self.assertGreater(one[0][1][0], 0.99)  # tissue
        self.assertEqual(one[1][1][0], 0.0)  # glass


if __name__ == "__main__":
    unittest.main()
