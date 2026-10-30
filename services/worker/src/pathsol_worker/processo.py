"""One job on VM2: from the WSI in the Blob to the .h5 in slide-h5 (skill pathsol-contrato-h5).

Everything happens in the job's work directory on the temporary disk, removed
at the end whatever happens (test 8). The outcome goes back to the consumer,
which writes it to the database before the message leaves the queue.
"""
import datetime
import json
import logging
import os
import shutil

import numpy as np

from pathsol_worker import consumidor, h5, passagem, versao
from pathsol_worker.slide import NO_SCALE, UnsupportedFormat

# The T4 saturates already at 32 patches (benchmark of 30/10).
BATCH = 32

log = logging.getLogger(__name__)


class Processor:
    def __init__(self, blob, extractor, extractor_version, software, workroot, workers=3):
        self.blob = blob
        self.extractor = extractor
        self.extractor_version = extractor_version
        self.path_hash = versao.short_hash(extractor_version)
        self.qc_version = versao.qc_version()
        self.software = json.dumps(software, sort_keys=True)
        self.workroot = workroot
        self.workers = workers

    def __call__(self, job):
        work = os.path.join(self.workroot, str(job.id))
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(work)
        try:
            return self._run(job, work)
        finally:
            shutil.rmtree(work, ignore_errors=True)

    def _run(self, job, work):
        wsi = os.path.join(work, job.blob_name)
        self.blob.download(job.container, job.blob_name, wsi, job.wsi_sha256)
        try:
            result = passagem.first_pass(wsi, job.material, work, self.workers)
        except UnsupportedFormat as refused:
            log.info("job %s: %s", job.id, refused.detail)
            return consumidor.Unsupported("scale_unavailable" if refused.reason == NO_SCALE else "format")
        name = f"{job.tenant_id}/{job.slide_id}/{self.path_hash}/{job.id}"
        attrs = {
            "tenant_id": str(job.tenant_id),
            "slide_id": str(job.slide_id),
            "wsi_sha256": job.wsi_sha256,
            "extractor": versao.MODEL,
            "extractor_version": self.extractor_version,
            "qc_version": self.qc_version,
            "versions": self.software,
            "created_at": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
        }
        if isinstance(result, passagem.QcRejected):
            if result.tiles is None:
                return consumidor.QcFailed(result.reason)
            path = os.path.join(work, "escores.qc.h5")
            _, _, md5 = h5.write_scores(path, result.tiles, attrs)
            self.blob.upload(f"{name}.qc.h5", path, md5)
            return consumidor.QcFailed(result.reason, f"{name}.qc.h5")
        if result.focus.warning:
            log.warning("job %s: %s", job.id, result.focus.warning)
        patches = result.patches
        embeddings = np.concatenate([self.extractor.embed(patches[i : i + BATCH]) for i in range(0, len(patches), BATCH)])
        path = os.path.join(work, "lamina.h5")
        size, sha256, md5 = h5.write(path, embeddings, result, attrs)
        self.blob.upload(f"{name}.h5", path, md5)
        return consumidor.Completed(f"{name}.h5", size, sha256, self.extractor_version)
