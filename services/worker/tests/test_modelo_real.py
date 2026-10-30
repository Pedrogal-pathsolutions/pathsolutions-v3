"""With the real Hibou-L files (PATHSOL_MODELO=<revision directory>); skipped otherwise.

The pinned revision loads offline as the class with registers, and the pixels
that reach the model through the worker's path equal those of the revision's
official processor on the same level-0 square.
"""
import os
import tempfile
import unittest

import numpy as np
import torch
from transformers import AutoImageProcessor

import sinteticas
from pathsol_worker import extractor
from pathsol_worker import slide as slides

MODEL_DIR = os.environ.get("PATHSOL_MODELO")


@unittest.skipUnless(MODEL_DIR, "sem PATHSOL_MODELO")
class RealModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ex = extractor.Extractor(MODEL_DIR, device="cpu", precision="fp32")

    def test_cls_of_the_pinned_revision(self):
        patches = np.random.default_rng(0).integers(0, 256, (2, 224, 224, 3), dtype=np.uint8)
        out = self.ex.embed(patches)
        self.assertEqual(out.shape, (2, 1024))
        self.assertTrue(np.isfinite(out).all())

    def test_same_pixels_as_the_official_processor(self):
        region = np.random.default_rng(1).integers(0, 256, (448, 448, 3), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, "l.svs")
            sinteticas.write_svs(path, region)
            with slides.open_slide(path) as s:
                patch = np.asarray(s.read_patch(0, 0, 448))
        processor = AutoImageProcessor.from_pretrained(MODEL_DIR, local_files_only=True, use_fast=False)
        official = processor(region, return_tensors="pt")["pixel_values"]
        seen = []
        hook = self.ex.model.register_forward_pre_hook(
            lambda module, args, kwargs: seen.append(kwargs["pixel_values"]), with_kwargs=True
        )
        try:
            self.ex.embed(patch[None])
        finally:
            hook.remove()
        torch.testing.assert_close(seen[0], official, rtol=0, atol=1e-5)


if __name__ == "__main__":
    unittest.main()
