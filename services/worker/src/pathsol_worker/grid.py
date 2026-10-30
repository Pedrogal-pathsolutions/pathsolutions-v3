"""Patch grid in level-0 pixels (skill pathsol-contrato-h5, "Grade e QC").

Every scanner and magnification lands on the same scale: a patch is the
level-0 square of side round(224 x 0.5 / mpp), resampled to 224 x 224.
"""
import numpy as np

PATCH = 224
TARGET_MPP = 0.5


def side_level0(mpp):
    return round(PATCH * TARGET_MPP / mpp)


def coordinates(width, height, side):
    """Top-left corners of the whole patches, from (0, 0), row by row."""
    xs = np.arange(0, width - side + 1, side, dtype=np.int32)
    ys = np.arange(0, height - side + 1, side, dtype=np.int32)
    if not len(xs) or not len(ys):
        return np.empty((0, 2), dtype=np.int32)
    gx, gy = np.meshgrid(xs, ys)
    return np.stack([gx.ravel(), gy.ravel()], axis=1)


def candidates(dimensions, mpp, mask, downsample):
    """(side, cells with any tissue in the thumbnail mask); QC 2 on the patch decides later."""
    side = side_level0(mpp)
    coords = coordinates(*dimensions, side)
    return side, coords[cell_fractions(mask, downsample, coords, side) > 0]


def cell_fractions(mask, downsample, coords, side):
    """Fraction of True mask pixels under each cell; the mask is downsample times smaller than level 0."""
    height, width = mask.shape
    integral = np.zeros((height + 1, width + 1), dtype=np.int64)
    integral[1:, 1:] = mask.cumsum(axis=0).cumsum(axis=1)
    x0 = np.clip(np.floor(coords[:, 0] / downsample).astype(np.int64), 0, width)
    y0 = np.clip(np.floor(coords[:, 1] / downsample).astype(np.int64), 0, height)
    x1 = np.clip(np.ceil((coords[:, 0] + side) / downsample).astype(np.int64), 0, width)
    y1 = np.clip(np.ceil((coords[:, 1] + side) / downsample).astype(np.int64), 0, height)
    area = (x1 - x0) * (y1 - y0)
    inside = integral[y1, x1] - integral[y0, x1] - integral[y1, x0] + integral[y0, x0]
    return np.divide(inside, area, out=np.zeros(len(coords)), where=area > 0)
