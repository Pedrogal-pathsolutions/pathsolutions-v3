"""The .h5 of a slide and the scores file of a focus block (skill pathsol-contrato-h5, "Esquema do arquivo").

Both are written in the job's work directory and read back before anything
is uploaded. write() returns size, sha256 and MD5; the MD5 goes with the
upload, so the Blob checks what it stored.
"""
import hashlib
import math

import h5py
import numpy as np

QC_COLUMNS = ("tissue_fraction", "laplacian_var", "tenengrad")
EMBEDDING_DIM = 1024


class InvalidH5(Exception):
    pass


def _common(f, tiles, attrs):
    f.create_dataset("coordinates", data=tiles.coordinates)
    f.create_dataset("qc_scores", data=tiles.scores).attrs["columns"] = QC_COLUMNS
    focus = tiles.focus
    f.attrs.update({
        **attrs,
        "mpp": tiles.mpp,
        "mpp_source": tiles.mpp_source,
        "reader": tiles.reader,
        # The Motic byte swap does not exist without the test export (decision 5).
        "header_patch": "none",
        "tile_size": tiles.side,
        "stride": tiles.side,
        "focus_p50": math.nan if focus.p50 is None else focus.p50,
        "focus_p90": math.nan if focus.p90 is None else focus.p90,
        "n_patches": len(tiles.coordinates),
        "n_rejected": tiles.rejected,
    })


def _check(path, n, embeddings):
    with h5py.File(path, "r") as f:
        same = (f["coordinates"].shape == (n, 2) and f["qc_scores"].shape == (n, len(QC_COLUMNS))
                and f.attrs["n_patches"] == n)
        if embeddings:
            same = same and f["embeddings"].shape == (n, EMBEDDING_DIM) and f["embeddings"].dtype == np.float32
    if not same:
        raise InvalidH5(f"{path}: o arquivo relido não confere")


def _digests(path):
    sha256, md5, size = hashlib.sha256(), hashlib.md5(), 0
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            sha256.update(chunk)
            md5.update(chunk)
            size += len(chunk)
    return size, sha256.hexdigest(), md5.digest()


def write(path, embeddings, tiles, attrs):
    n = len(tiles.coordinates)
    if embeddings.shape != (n, EMBEDDING_DIM) or not np.isfinite(embeddings).all():
        raise InvalidH5(f"embeddings {embeddings.shape} para {n} patches, ou com NaN ou Inf")
    with h5py.File(path, "w") as f:
        f.create_dataset("embeddings", data=embeddings.astype(np.float32))
        _common(f, tiles, attrs)
    _check(path, n, embeddings=True)
    return _digests(path)


def write_scores(path, tiles, attrs):
    with h5py.File(path, "w") as f:
        _common(f, tiles, attrs)
    _check(path, len(tiles.coordinates), embeddings=False)
    return _digests(path)
