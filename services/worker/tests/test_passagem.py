import os
import tempfile
import unittest
from unittest import mock

import cv2
import numpy as np

import sinteticas
from pathsol_worker import passagem, qc
from pathsol_worker import slide as slides

SIDE = 224  # at 0.5 um/px a patch is 224 level-0 pixels
CELLS = 13  # 169 patches, above the focus minimum


def textured(size, rng):
    """Pink tissue with fine texture: a high Laplacian, as in focus."""
    image = np.empty((size, size, 3), dtype=np.uint8)
    noise = rng.integers(-40, 41, (size, size, 1))
    image[:] = np.clip(np.array((200, 120, 170)) + noise, 0, 255)
    return image


class FirstPass(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.rng = np.random.default_rng(0)

    def svs(self, image, name="l.svs"):
        path = os.path.join(self.dir.name, name)
        sinteticas.write_svs(path, image, mpp=0.5)
        return path

    def work(self):
        return tempfile.mkdtemp(dir=self.dir.name)

    def tissue_slide(self, blurred_fraction=0.0):
        """CELLS x CELLS cells of tissue inside one cell of glass, as on a real slide."""
        size = SIDE * CELLS
        tissue = textured(size, self.rng)
        cut = int(size * blurred_fraction)
        if cut:
            tissue[:, :cut] = cv2.GaussianBlur(tissue[:, :cut], (0, 0), 6)
        image = np.full((size + 2 * SIDE, size + 2 * SIDE, 3), 240, dtype=np.uint8)
        image[SIDE:-SIDE, SIDE:-SIDE] = tissue
        return self.svs(image)

    def test_blank_glass_fails_qc1_before_any_tile(self):
        glass = np.clip(240 + self.rng.integers(-3, 4, (2048, 2048, 3)), 0, 255).astype(np.uint8)
        work = self.work()
        result = passagem.first_pass(self.svs(glass), "biopsia", work, workers=1)
        self.assertEqual(result, passagem.QcRejected("empty_glass", None))
        self.assertEqual(os.listdir(work), [])

    def test_tiny_tissue_is_insufficient_except_in_cytology(self):
        image = np.full((2048, 2048, 3), 240, dtype=np.uint8)
        image[800:1200, 800:1200] = textured(400, self.rng)  # 200 x 200 um: 0.04 mm2
        path = self.svs(image)
        self.assertEqual(passagem.first_pass(path, "biopsia", self.work(), workers=1).reason, "insufficient_material")
        self.assertIsInstance(passagem.first_pass(path, "citologia", self.work(), workers=1), passagem.Tiles)

    def test_sharp_tissue_gives_tiles_and_the_patches_kept_on_disk(self):
        path = self.tissue_slide()
        work = self.work()
        tiles = passagem.first_pass(path, "biopsia", work, workers=2)
        self.assertIsInstance(tiles, passagem.Tiles)
        self.assertEqual(tiles.side, SIDE)
        self.assertEqual(len(tiles.coordinates), CELLS * CELLS)
        self.assertEqual(tiles.coordinates.dtype, np.int32)
        self.assertTrue((tiles.coordinates % SIDE == 0).all())
        self.assertEqual(tiles.scores.shape, (CELLS * CELLS, 3))
        self.assertEqual(tiles.patches.shape, (CELLS * CELLS, 224, 224, 3))
        x, y = tiles.coordinates[7]
        with slides.open_slide(path) as s:
            np.testing.assert_array_equal(tiles.patches[7], np.asarray(s.read_patch(x, y, SIDE)))
        self.assertFalse(tiles.focus.blocked)
        self.assertGreater(tiles.focus.p90, tiles.focus.p50 * 0.5)
        self.assertEqual(tiles.mpp, 0.5)

    def test_same_slide_same_patches_and_scores(self):
        path = self.tissue_slide()
        first = passagem.first_pass(path, "biopsia", self.work(), workers=2)
        again = passagem.first_pass(path, "biopsia", self.work(), workers=1)
        np.testing.assert_array_equal(first.coordinates, again.coordinates)
        np.testing.assert_array_equal(first.scores, again.scores)

    def test_blurred_slide_is_blocked_before_the_gpu_with_its_scores(self):
        result = passagem.first_pass(self.tissue_slide(blurred_fraction=0.4), "biopsia", self.work(), workers=2)
        self.assertEqual(result.reason, "focus")
        self.assertGreater(result.tiles.focus.out_of_focus, qc.FOCUS_BLOCK)
        self.assertEqual(len(result.tiles.scores), len(result.tiles.coordinates))

    def test_blurred_cytology_is_recorded_not_blocked(self):
        tiles = passagem.first_pass(self.tissue_slide(blurred_fraction=0.4), "citologia", self.work(), workers=2)
        self.assertIsInstance(tiles, passagem.Tiles)
        self.assertGreater(tiles.focus.out_of_focus, qc.FOCUS_BLOCK)

    def test_refuses_to_start_above_the_work_cap(self):
        path = self.tissue_slide()
        with mock.patch.object(passagem, "MAX_WORK_BYTES", 1000), self.assertRaises(passagem.WorkTooLarge):
            passagem.first_pass(path, "biopsia", self.work(), workers=1)


if __name__ == "__main__":
    unittest.main()
