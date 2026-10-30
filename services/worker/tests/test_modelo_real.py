"""With the real Hibou-L files (PATHSOL_MODELO=<revision directory>); skipped otherwise.

The pinned revision loads offline as the class with registers, and the pixels
that reach the model through the worker's path equal those of the revision's
official processor on the same level-0 square.
"""
import json
import os
import shutil
import tempfile
import unittest
import uuid

import h5py
import numpy as np
import torch
from transformers import AutoImageProcessor

import sinteticas
from pathsol_worker import banco, consumidor, extractor, processo, versao
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

    def test_a_whole_job_with_the_real_model(self):
        with tempfile.TemporaryDirectory() as directory:
            source = sinteticas.tissue_slide(os.path.join(directory, "l.svs"), np.random.default_rng(2), cells=3)
            work = os.path.join(directory, "trabalho")
            os.makedirs(work)
            uploads = {}

            class LocalBlob:
                def download(self, container, name, path, sha256):
                    shutil.copy(source, path)

                def upload(self, name, path, md5):
                    shutil.copy(path, os.path.join(directory, "enviado.h5"))
                    uploads[name] = md5

            version = versao.extractor_version(MODEL_DIR)
            job = banco.Job(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "wsi-publico", "l.svs", "0" * 64,
                            "estomago", "biopsia", "HE", "RUNNING", 0)
            outcome = processo.Processor(LocalBlob(), self.ex, version, versao.software(), work, workers=1)(job)
            self.assertIsInstance(outcome, consumidor.Completed)
            self.assertIn(f"/{versao.short_hash(version)}/{job.id}.h5", outcome.h5_blob)
            with h5py.File(os.path.join(directory, "enviado.h5")) as f:
                embeddings = f["embeddings"][:]
                self.assertEqual(json.loads(f.attrs["extractor_version"])["arquivos"]["model.safetensors"],
                                 "a63d1699448143ceccf2b7e1c4bf35b995c51f86ef8a6efb471af2eee210b79c")
            self.assertEqual(embeddings.shape, (9, 1024))
            self.assertTrue(np.isfinite(embeddings).all())
            self.assertEqual(os.listdir(work), [])


if __name__ == "__main__":
    unittest.main()
