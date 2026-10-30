"""Reads patches and their QC 2 metrics in worker processes (plan, section 10.4).

QC 2 runs on the CPU, before the GPU. The processes are spawned, never
forked, so a CUDA context in the parent is never copied, and they never
import torch.
"""
import multiprocessing

import cv2
import numpy as np

from pathsol_worker import qc
from pathsol_worker.slide import open_slide

_slide = None
_threshold = None


def _start(path, threshold):
    global _slide, _threshold
    # One thread each: the processes already split the CPUs.
    cv2.setNumThreads(1)
    _slide = open_slide(path)
    _threshold = threshold


def _read(cell):
    x, y, side = cell
    patch = np.asarray(_slide.read_patch(x, y, side))
    return patch, qc.patch_metrics(patch, _threshold)


def read_patches(path, coords, side, threshold, workers, chunksize=8):
    """Yields (224 x 224 x 3 uint8 patch, (tissue fraction, Laplacian, Tenengrad)) in the order of coords."""
    cells = ((int(x), int(y), side) for x, y in coords)
    if workers <= 1:
        _start(path, threshold)
        try:
            yield from map(_read, cells)
        finally:
            _slide.close()
        return
    with multiprocessing.get_context("spawn").Pool(workers, _start, (path, threshold)) as pool:
        yield from pool.imap(_read, cells, chunksize)
