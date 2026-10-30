import unittest

import numpy as np

from pathsol_worker import grid


class Side(unittest.TestCase):
    def test_side_in_level0_pixels_for_0_5_um(self):
        self.assertEqual(grid.side_level0(0.25), 448)
        self.assertEqual(grid.side_level0(0.5), 224)
        self.assertEqual(grid.side_level0(0.2527), 443)
        self.assertEqual(grid.side_level0(0.52), 215)


class Coordinates(unittest.TestCase):
    def test_whole_patches_from_the_origin_row_by_row(self):
        coords = grid.coordinates(1000, 500, 224)
        self.assertEqual(coords.dtype, np.int32)
        expected = [(x, y) for y in (0, 224) for x in (0, 224, 448, 672)]
        self.assertEqual([tuple(c) for c in coords], expected)

    def test_no_patch_when_the_slide_is_smaller_than_one(self):
        self.assertEqual(grid.coordinates(100, 500, 224).shape, (0, 2))


class CellFractions(unittest.TestCase):
    def test_fraction_of_mask_under_each_cell(self):
        # Mask at downsample 4: each mask pixel covers 4x4 level-0 pixels.
        mask = np.zeros((10, 20), dtype=bool)
        mask[:, :5] = True  # level-0 x from 0 to 20
        coords = np.array([[0, 0], [8, 0], [16, 0], [40, 0]], dtype=np.int32)
        fractions = grid.cell_fractions(mask, 4.0, coords, 8)
        np.testing.assert_allclose(fractions, [1.0, 1.0, 0.5, 0.0])

    def test_cell_past_the_mask_border_counts_only_what_is_inside(self):
        mask = np.ones((2, 2), dtype=bool)
        fractions = grid.cell_fractions(mask, 4.0, np.array([[4, 4]], dtype=np.int32), 8)
        np.testing.assert_allclose(fractions, [1.0])

    def test_fractional_downsample(self):
        mask = np.zeros((10, 10), dtype=bool)
        mask[0:5, 0:5] = True
        # 2.5 level-0 pixels per mask pixel: the cell at (0, 0) of side 10 covers mask [0, 4).
        fractions = grid.cell_fractions(mask, 2.5, np.array([[0, 0], [15, 15]], dtype=np.int32), 10)
        np.testing.assert_allclose(fractions, [1.0, 0.0])


if __name__ == "__main__":
    unittest.main()
