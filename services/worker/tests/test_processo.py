import os
import shutil
import tempfile
import unittest
import uuid

import h5py
import numpy as np

import sinteticas
from pathsol_worker import banco, consumidor, processo, versao

VERSION = '{"extrator":"teste"}'


class FakeBlob:
    def __init__(self, source):
        self.source = source
        self.uploads = {}

    def download(self, container, name, path, sha256):
        shutil.copy(self.source, path)

    def upload(self, name, path, md5):
        with open(path, "rb") as f:
            self.uploads[name] = f.read()


class FakeExtractor:
    def __init__(self):
        self.batches = []

    def embed(self, patches):
        self.batches.append(len(patches))
        return np.ones((len(patches), 1024), dtype=np.float32)


class Process(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)
        self.workroot = os.path.join(self.dir.name, "trabalho")
        os.makedirs(self.workroot)
        self.rng = np.random.default_rng(1)
        self.job = banco.Job(uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), "wsi-publico", "x.svs", "e" * 64,
                             "estomago", "biopsia", "HE", "RUNNING", 0)

    def run_job(self, source, job=None):
        blob, extractor = FakeBlob(source), FakeExtractor()
        worker = processo.Processor(blob, extractor, VERSION, {"torch": "teste"}, self.workroot, workers=1)
        outcome = worker(job or self.job)
        return outcome, blob, extractor

    def name(self, suffix):
        return f"{self.job.tenant_id}/{self.job.slide_id}/{versao.short_hash(VERSION)}/{self.job.id}.{suffix}"

    def test_tissue_becomes_an_h5_named_by_the_job(self):
        source = sinteticas.tissue_slide(os.path.join(self.dir.name, "l.svs"), self.rng, cells=6)
        outcome, blob, extractor = self.run_job(source)
        self.assertIsInstance(outcome, consumidor.Completed)
        self.assertEqual(outcome.h5_blob, self.name("h5"))
        self.assertEqual(outcome.extractor_version, VERSION)
        self.assertEqual(set(blob.uploads), {self.name("h5")})
        path = os.path.join(self.dir.name, "baixado.h5")
        with open(path, "wb") as f:
            f.write(blob.uploads[self.name("h5")])
        with h5py.File(path) as f:
            self.assertEqual(f["embeddings"].shape, (36, 1024))
            self.assertEqual(f.attrs["extractor_version"], VERSION)
            self.assertEqual(f.attrs["slide_id"], str(self.job.slide_id))
        self.assertEqual(sum(extractor.batches), 36)
        self.assertLessEqual(max(extractor.batches), processo.BATCH)
        self.assertEqual(os.listdir(self.workroot), [])

    def test_focus_block_uploads_the_scores_without_the_gpu(self):
        source = sinteticas.tissue_slide(os.path.join(self.dir.name, "l.svs"), self.rng, blurred_fraction=0.4)
        outcome, blob, extractor = self.run_job(source)
        self.assertEqual(outcome, consumidor.QcFailed("focus", self.name("qc.h5")))
        self.assertEqual(set(blob.uploads), {self.name("qc.h5")})
        self.assertEqual(extractor.batches, [])
        self.assertEqual(os.listdir(self.workroot), [])

    def test_empty_glass_ends_without_gpu_or_upload(self):
        source = os.path.join(self.dir.name, "vazia.svs")
        sinteticas.write_svs(source, np.full((2048, 2048, 3), 240, dtype=np.uint8), mpp=0.5)
        outcome, blob, extractor = self.run_job(source)
        self.assertEqual(outcome, consumidor.QcFailed("empty_glass"))
        self.assertEqual((blob.uploads, extractor.batches), ({}, []))

    def test_refused_slides_tell_the_lab_why(self):
        image = sinteticas.tissue_image()
        cases = ((dict(mpp=0.9), "scale_unavailable"), (dict(description="generic tiff"), "format"))
        for kwargs, reason in cases:
            with self.subTest(reason=reason):
                source = os.path.join(self.dir.name, f"{reason}.svs")
                sinteticas.write_svs(source, image, **kwargs)
                outcome, _, extractor = self.run_job(source)
                self.assertEqual(outcome, consumidor.Unsupported(reason))
                self.assertEqual(extractor.batches, [])

    def test_work_directory_goes_even_when_the_download_fails(self):
        class Broken(FakeBlob):
            def download(self, container, name, path, sha256):
                with open(path, "wb") as f:
                    f.write(b"parcial")
                raise OSError("rede")

        worker = processo.Processor(Broken(None), FakeExtractor(), VERSION, {}, self.workroot, workers=1)
        with self.assertRaises(OSError):
            worker(self.job)
        self.assertEqual(os.listdir(self.workroot), [])


if __name__ == "__main__":
    unittest.main()
