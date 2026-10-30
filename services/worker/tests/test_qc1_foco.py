import unittest

import numpy as np

from pathsol_worker import qc

PINK = (200, 120, 170)
PURPLE = (120, 60, 160)  # hematoxylin-like: tissue, not ink
BLUE_INK = (40, 60, 200)
GREEN_INK = (40, 160, 60)
GLASS = (240, 240, 240)
MPP = 4.0  # thumbnail scale


def thumb(size=(200, 300)):
    return np.full((*size, 3), GLASS, dtype=np.uint8)


class TissueMask(unittest.TestCase):
    def test_pen_ink_is_not_tissue_but_hematoxylin_is(self):
        image = thumb()
        image[20:80, 20:80] = PINK
        image[20:80, 100:160] = PURPLE
        image[120:180, 20:80] = BLUE_INK
        image[120:180, 100:160] = GREEN_INK
        mask, _ = qc.qc1_mask(image, MPP)
        self.assertTrue(mask[30:70, 30:70].all())
        self.assertTrue(mask[30:70, 110:150].all())
        self.assertFalse(mask[120:180, 20:80].any())
        self.assertFalse(mask[120:180, 100:160].any())

    def test_specks_are_dropped_and_holes_filled(self):
        image = thumb()
        image[50:150, 50:150] = PINK
        image[90:100, 90:100] = GLASS  # a hole of 40 um inside the fragment
        image[10:12, 250:252] = PINK  # a speck of 8 um: dust
        mask, _ = qc.qc1_mask(image, MPP)
        self.assertTrue(mask[90:100, 90:100].all())
        self.assertFalse(mask[5:20, 240:260].any())

    def test_area_in_square_millimetres(self):
        image = thumb()
        image[0:100, 0:100] = PINK  # 400 x 400 um
        mask, _ = qc.qc1_mask(image, MPP)
        self.assertAlmostEqual(qc.area_mm2(mask, MPP), 0.16, delta=0.01)


class Qc1Decision(unittest.TestCase):
    def test_empty_glass_for_every_material(self):
        for material in ("biopsia", "peca", "citologia"):
            with self.subTest(material=material):
                self.assertEqual(qc.qc1_failure(0.0, material), "empty_glass")

    def test_too_little_tissue_except_cytology(self):
        small = (qc.EMPTY_MM2 + qc.MIN_TISSUE_MM2["biopsia"]) / 2
        self.assertEqual(qc.qc1_failure(small, "biopsia"), "insufficient_material")
        self.assertEqual(qc.qc1_failure(small, "peca"), "insufficient_material")
        self.assertIsNone(qc.qc1_failure(small, "citologia"))

    def test_enough_tissue(self):
        self.assertIsNone(qc.qc1_failure(qc.MIN_TISSUE_MM2["peca"] * 2, "peca"))


def scores(n, sharp=100.0, blurred=0, tissue=0.9):
    """Rows of (tissue fraction, Laplacian, Tenengrad)."""
    lap = np.full(n, sharp)
    lap[:blurred] = sharp * 0.01
    return np.column_stack([np.full(n, tissue), lap, lap * 3]).astype(np.float32)


class FocusRule(unittest.TestCase):
    def test_blocks_above_a_fifth_of_the_patches_out_of_focus(self):
        decision = qc.focus(scores(200, blurred=60), "biopsia")
        self.assertTrue(decision.blocked)
        self.assertAlmostEqual(decision.out_of_focus, 0.30)

    def test_keeps_a_slide_with_few_blurred_patches(self):
        decision = qc.focus(scores(200, blurred=20), "biopsia")
        self.assertFalse(decision.blocked)
        self.assertIsNone(decision.warning)

    def test_only_patches_with_more_than_half_tissue_count(self):
        rows = np.vstack([scores(200, blurred=10), scores(200, blurred=200, tissue=0.4)])
        self.assertFalse(qc.focus(rows, "biopsia").blocked)

    def test_cytology_is_recorded_and_never_blocked(self):
        decision = qc.focus(scores(200, blurred=150), "citologia")
        self.assertFalse(decision.blocked)
        self.assertAlmostEqual(decision.out_of_focus, 0.75)

    def test_too_few_patches_only_warn(self):
        decision = qc.focus(scores(qc.FOCUS_MIN_PATCHES - 1, blurred=100), "biopsia")
        self.assertFalse(decision.blocked)
        self.assertIsNotNone(decision.warning)

    def test_percentiles_of_the_counted_patches(self):
        decision = qc.focus(scores(200), "peca")
        self.assertEqual((decision.p50, decision.p90), (100.0, 100.0))

    def test_no_patch_to_measure(self):
        decision = qc.focus(np.empty((0, 3), dtype=np.float32), "biopsia")
        self.assertFalse(decision.blocked)
        self.assertIsNone(decision.p90)
        self.assertIsNotNone(decision.warning)


if __name__ == "__main__":
    unittest.main()
