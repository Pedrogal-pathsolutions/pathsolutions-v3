"""First pass over a slide, all on the CPU (plan, sections 10.3 to 10.6; skill pathsol-contrato-h5).

QC 1 on the thumbnail, the grid, and QC 2 on every candidate. The patches at
or above the extraction floor stay in a memory-mapped file in the job's work
directory, so the GPU never reads the slide again; the focus rule is decided
before any GPU work, and a blocked slide never reaches Hibou-L.
"""
import dataclasses
import os
import shutil

import numpy as np

from pathsol_worker import grid, patches, qc
from pathsol_worker.slide import open_slide

PATCH_BYTES = grid.PATCH * grid.PATCH * 3
# Cap of the kept patches in the work directory, on VM2's temporary disk.
MAX_WORK_BYTES = 40 * 1024**3
FREE_MARGIN = 2 * 1024**3


class WorkTooLarge(Exception):
    """More candidates than the work directory may hold: a technical failure."""


@dataclasses.dataclass(frozen=True, eq=False)
class Tiles:
    coordinates: np.ndarray
    scores: np.ndarray
    patches: np.ndarray
    side: int
    rejected: int
    focus: qc.Focus
    area_mm2: float
    mpp: float
    mpp_source: str
    reader: str


@dataclasses.dataclass(frozen=True)
class QcRejected:
    """QC_FAILED; for focus, with the tiles whose scores go to the scores file."""

    reason: str
    tiles: Tiles | None


def first_pass(path, material, workdir, workers=3):
    """Tiles to extract, or QcRejected. A slide the reader refuses raises slide.UnsupportedFormat."""
    with open_slide(path) as s:
        mask, downsample, threshold, area = qc.thumbnail_mask(s)
        failure = qc.qc1_failure(area, material)
        if failure:
            return QcRejected(failure, None)
        side, cells = grid.candidates(s.dimensions, s.mpp, mask, downsample)
        meta = {"area_mm2": area, "mpp": s.mpp, "mpp_source": s.mpp_source, "reader": s.reader}
    need = len(cells) * PATCH_BYTES
    if need > MAX_WORK_BYTES or shutil.disk_usage(workdir).free < need + FREE_MARGIN:
        raise WorkTooLarge(f"{len(cells)} candidatos, {need} bytes de patches")
    kept = np.memmap(os.path.join(workdir, "patches.u8"), dtype=np.uint8, mode="w+",
                     shape=(max(len(cells), 1), grid.PATCH, grid.PATCH, 3))
    coordinates, scores = [], []
    for (x, y), (patch, metrics) in zip(cells, patches.read_patches(path, cells, side, threshold, workers)):
        if metrics[0] < qc.EXTRACTION_FLOOR:
            continue
        kept[len(coordinates)] = patch
        coordinates.append((x, y))
        scores.append(metrics)
    kept.flush()
    if not coordinates:
        # QC 1 saw tissue, but no patch reaches the floor: nothing to extract.
        return QcRejected("insufficient_material", None)
    scores = np.array(scores, dtype=np.float32)
    tiles = Tiles(np.array(coordinates, dtype=np.int32), scores, kept[: len(coordinates)], side,
                  len(cells) - len(coordinates), qc.focus(scores, material), **meta)
    return QcRejected("focus", tiles) if tiles.focus.blocked else tiles
