import os
import tempfile
import unittest

import numpy as np

import sinteticas
from pathsol_worker import benchmark


class FakeExtractor:
    """Embeds a patch as its mean colour, repeated: cosine 1 between twins."""

    def __init__(self, sign=1.0):
        self.sign = sign
        self.batches = []

    def embed(self, patches):
        self.batches.append(len(patches))
        means = patches.reshape(len(patches), -1).mean(axis=1, dtype=np.float32) + 1
        return self.sign * np.repeat(means[:, None], 1024, axis=1)


class Cosine(unittest.TestCase):
    def test_same_and_opposite_rows(self):
        a = np.array([[1.0, 0.0], [0.0, 2.0]], dtype=np.float32)
        np.testing.assert_allclose(benchmark.row_cosine(a, a), [1.0, 1.0])
        np.testing.assert_allclose(benchmark.row_cosine(a, -a), [-1.0, -1.0])


class Slide(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.path = os.path.join(self.dir.name, "l.svs")
        image = np.full((2048, 4096, 3), 240, dtype=np.uint8)
        image[:896, :1344] = (200, 120, 170)  # six whole cells of tissue
        # A 60 x 60 um fragment on the corner of four cells: it survives QC 1, and each cell gets ~7% tissue.
        image[328:568, 2568:2808] = (200, 120, 170)
        sinteticas.write_svs(self.path, image)

    def test_every_candidate_is_extracted_or_below_the_floor(self):
        fp16, fp32 = FakeExtractor(), FakeExtractor()
        result = benchmark.bench_slide(self.path, fp16, fp32, batch=4, workers=2, cpu_workers=(1, 2), sample=20)
        self.assertGreater(result["extraidos"], 0)
        self.assertGreater(result["rejeitados"], 0)
        self.assertEqual(result["extraidos"] + result["rejeitados"], result["candidatos"])
        self.assertEqual(sum(fp16.batches), result["extraidos"])
        self.assertLessEqual(max(fp16.batches), 4)
        self.assertEqual([c["processos"] for c in result["cpu"]], [1, 2])
        self.assertEqual(result["lado_nivel0"], 448)
        self.assertAlmostEqual(result["cosseno_fp16_fp32"]["media"], 1.0, places=6)
        self.assertFalse(result["cosseno_fp16_fp32"]["nan_inf"])

    def test_nan_in_one_precision_is_reported(self):
        class NaNExtractor(FakeExtractor):
            def embed(self, patches):
                out = super().embed(patches)
                out[0, 0] = np.nan
                return out

        result = benchmark.bench_slide(self.path, FakeExtractor(), NaNExtractor(), batch=4, workers=1, cpu_workers=(1,), sample=8)
        self.assertTrue(result["cosseno_fp16_fp32"]["nan_inf"])


if __name__ == "__main__":
    unittest.main()
