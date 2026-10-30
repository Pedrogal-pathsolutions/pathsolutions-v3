import hashlib
import json
import os
import tempfile
import unittest
import uuid

import h5py
import numpy as np

from pathsol_worker import h5, passagem, qc, versao


def model_dir(root, weights=b"pesos"):
    files = {"model.safetensors": weights, "config.json": b"{}", "preprocessor_config.json": b"{}",
             "configuration_dinov2.py": b"# c", "modeling_dinov2.py": b"# m", "README.md": b"card"}
    for name, content in files.items():
        with open(os.path.join(root, name), "wb") as f:
            f.write(content)
    return root


def tiles(n=5):
    coords = np.arange(n * 2, dtype=np.int32).reshape(n, 2) * 448
    scores = np.tile(np.array([[0.9, 100.0, 300.0]], dtype=np.float32), (n, 1))
    patches = np.zeros((n, 224, 224, 3), dtype=np.uint8)
    focus = qc.Focus(False, 0.0, 100.0, 100.0, None)
    return passagem.Tiles(coords, scores, patches, 448, 2, focus, 1.5, 0.25, "openslide.mpp-x/mpp-y", "openslide 4.0.1 (openslide-python 1.4.6)")


class Versions(unittest.TestCase):
    def test_extractor_version_is_canonical_and_follows_every_model_file(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = versao.extractor_version(model_dir(a))
            self.assertEqual(first, versao.extractor_version(model_dir(b)))
            changed = versao.extractor_version(model_dir(b, weights=b"outros pesos"))
        self.assertNotEqual(first, changed)
        parts = json.loads(first)
        self.assertEqual(parts["arquivos"]["model.safetensors"], hashlib.sha256(b"pesos").hexdigest())
        self.assertNotIn("README.md", parts["arquivos"])
        for key in ("preprocessamento", "normalizacao", "token", "patch", "stride", "mpp", "precisao", "atencao"):
            self.assertIn(key, parts)
        self.assertEqual(parts["atencao"], "eager")
        self.assertEqual(json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False), first)

    def test_short_hash_for_the_path(self):
        self.assertRegex(versao.short_hash("abc"), r"^[0-9a-f]{12}$")

    def test_qc_version_follows_the_floor(self):
        before = versao.qc_version()
        self.assertIn('"piso_extracao":0.1', before)
        qc.EXTRACTION_FLOOR, old = 0.2, qc.EXTRACTION_FLOOR
        try:
            self.assertNotEqual(versao.qc_version(), before)
        finally:
            qc.EXTRACTION_FLOOR = old


class Write(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.attrs = {"tenant_id": str(uuid.uuid4()), "slide_id": str(uuid.uuid4()), "wsi_sha256": "d" * 64,
                      "extractor": "histai/hibou-L@x", "extractor_version": "{}", "qc_version": "{}",
                      "versions": json.dumps({"torch": "x"}), "created_at": "2026-10-30T20:00:00+00:00"}

    def test_schema_of_the_contract(self):
        path = os.path.join(self.dir.name, "j.h5")
        t = tiles()
        embeddings = np.ones((5, 1024), dtype=np.float32)
        size, sha256, md5 = h5.write(path, embeddings, t, self.attrs)
        self.assertEqual(size, os.path.getsize(path))
        with open(path, "rb") as f:
            content = f.read()
        self.assertEqual(sha256, hashlib.sha256(content).hexdigest())
        self.assertEqual(md5, hashlib.md5(content).digest())
        with h5py.File(path) as f:
            self.assertEqual((f["embeddings"].shape, f["embeddings"].dtype), ((5, 1024), np.float32))
            self.assertEqual((f["coordinates"].shape, f["coordinates"].dtype), ((5, 2), np.int32))
            self.assertEqual((f["qc_scores"].shape, f["qc_scores"].dtype), ((5, 3), np.float32))
            self.assertEqual(list(f["qc_scores"].attrs["columns"]), list(h5.QC_COLUMNS))
            attrs = dict(f.attrs)
        self.assertEqual((attrs["tile_size"], attrs["stride"], attrs["n_patches"], attrs["n_rejected"]), (448, 448, 5, 2))
        self.assertEqual((attrs["mpp"], attrs["header_patch"]), (0.25, "none"))
        self.assertEqual((attrs["focus_p50"], attrs["focus_p90"]), (100.0, 100.0))
        for key in ("tenant_id", "slide_id", "wsi_sha256", "mpp_source", "reader", "extractor", "extractor_version",
                    "qc_version", "versions", "created_at"):
            self.assertIn(key, attrs)
        for key in ("case_id", "magnification"):
            self.assertNotIn(key, attrs)

    def test_refuses_embeddings_that_do_not_match_the_tiles(self):
        path = os.path.join(self.dir.name, "j.h5")
        for bad in (np.ones((4, 1024), np.float32), np.ones((5, 768), np.float32), np.full((5, 1024), np.nan, np.float32)):
            with self.subTest(shape=bad.shape), self.assertRaises(h5.InvalidH5):
                h5.write(path, bad, tiles(), self.attrs)

    def test_scores_file_of_a_focus_block_has_no_embeddings(self):
        path = os.path.join(self.dir.name, "j.qc.h5")
        h5.write_scores(path, tiles(), self.attrs)
        with h5py.File(path) as f:
            self.assertNotIn("embeddings", f)
            self.assertEqual(f["qc_scores"].shape, (5, 3))
            self.assertEqual(f["coordinates"].shape, (5, 2))


if __name__ == "__main__":
    unittest.main()
