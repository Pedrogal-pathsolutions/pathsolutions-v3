"""QC 1, QC 2 and the focus rule (plan, sections 10.4 to 10.6; skill pathsol-contrato-h5).

Tissue is saturation above a per-slide Otsu threshold, which never drops below
a floor, so blank glass and its noise read as no tissue; pen ink is not
tissue. Focus is measured on the luminance, only where tissue surrounds the
pixel: the 3 x 3 kernels at the tissue border would otherwise also see the
glass. Every number below is provisional until calibrated on the acceptance
slides, and part of qc_version.
"""
import dataclasses

import cv2
import numpy as np

MIN_SATURATION = 15
FOCUS_NEIGHBOURHOOD = np.ones((3, 3), dtype=np.uint8)
# Pen ink by hue on OpenCV's 0-180 scale (green and blue markers) and near-black;
# hematoxylin's violet, around 130-150, stays tissue.
PEN_HUES = ((35, 85), (95, 125))
PEN_MIN_SATURATION = 100
PEN_MAX_VALUE = 50

# QC 1 works on a thumbnail of about 2 to 8 µm/px.
QC1_MPP = 4.0
MORPHOLOGY_UM = 20
MIN_FRAGMENT_UM2 = 2500
EMPTY_MM2 = 0.02
# Conservative: a small endoscopic biopsy must pass. Cytology fails only on empty glass.
MIN_TISSUE_MM2 = {"biopsia": 0.1, "peca": 0.5}

# Patches with 10% or more tissue go to Hibou-L; the head's configuration
# decides later which of them it uses.
EXTRACTION_FLOOR = 0.10

# Plan 10.5: relative cut per slide, among the patches with more than half tissue.
FOCUS_TISSUE = 0.5
FOCUS_RELATIVE = 0.10
FOCUS_BLOCK = 0.20
FOCUS_MIN_PATCHES = 150


def saturation(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1]


def tissue_threshold(thumb_rgb):
    otsu, _ = cv2.threshold(saturation(thumb_rgb), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return max(int(otsu), MIN_SATURATION)


def tissue_mask(rgb, threshold):
    hue, sat, val = np.moveaxis(cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV), -1, 0)
    ink = val < PEN_MAX_VALUE
    for low, high in PEN_HUES:
        ink |= (hue >= low) & (hue <= high) & (sat > PEN_MIN_SATURATION)
    return (sat > threshold) & ~ink


def _fill_holes(mask):
    flood = np.pad(mask, 1).astype(np.uint8)
    cv2.floodFill(flood, None, (0, 0), 1)
    return mask | (flood[1:-1, 1:-1] == 0)


def _drop_small(mask, min_pixels):
    count, labels, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    keep = np.zeros(count, dtype=bool)
    keep[1:] = stats[1:, cv2.CC_STAT_AREA] >= min_pixels
    return keep[labels]


def qc1_mask(thumb_rgb, mpp):
    """(tissue mask of the thumbnail, cleaned in µm, and the slide's tissue threshold)."""
    threshold = tissue_threshold(thumb_rgb)
    side = max(3, round(MORPHOLOGY_UM / mpp) | 1)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (side, side))
    mask = tissue_mask(thumb_rgb, threshold).astype(np.uint8)
    mask = cv2.morphologyEx(cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel), cv2.MORPH_CLOSE, kernel) > 0
    return _drop_small(_fill_holes(mask), MIN_FRAGMENT_UM2 / mpp**2), threshold


def area_mm2(mask, mpp):
    return float(mask.sum()) * mpp * mpp / 1e6


def qc1_failure(area, material):
    """The QC_FAILED reason of QC 1, or None."""
    if area < EMPTY_MM2:
        return "empty_glass"
    if area < MIN_TISSUE_MM2.get(material, 0.0):
        return "insufficient_material"
    return None


def thumbnail_mask(slide):
    """QC 1 on the slide: (tissue mask, level-0 pixels per mask pixel, threshold, tissue area in mm²)."""
    thumb, downsample = slide.thumbnail(QC1_MPP)
    mpp = slide.mpp * downsample
    mask, threshold = qc1_mask(thumb, mpp)
    return mask, downsample, threshold, area_mm2(mask, mpp)


def patch_metrics(rgb, threshold):
    """(tissue fraction, Laplacian variance, Tenengrad) of one patch at the working scale."""
    tissue = tissue_mask(rgb, threshold)
    fraction = float(tissue.mean())
    inner = cv2.erode(tissue.astype(np.uint8), FOCUS_NEIGHBOURHOOD, borderType=cv2.BORDER_CONSTANT, borderValue=0) > 0
    if not inner.any():
        return fraction, 0.0, 0.0
    luminance = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float64)
    laplacian = cv2.Laplacian(luminance, cv2.CV_64F)[inner]
    gx = cv2.Sobel(luminance, cv2.CV_64F, 1, 0)[inner]
    gy = cv2.Sobel(luminance, cv2.CV_64F, 0, 1)[inner]
    return fraction, float(laplacian.var()), float((gx * gx + gy * gy).mean())


@dataclasses.dataclass(frozen=True)
class Focus:
    blocked: bool
    out_of_focus: float | None
    p50: float | None
    p90: float | None
    warning: str | None


def focus(scores, material):
    """The focus rule on the QC 2 rows (tissue fraction, Laplacian, Tenengrad) of a slide."""
    laplacian = scores[scores[:, 0] > FOCUS_TISSUE, 1]
    if not len(laplacian):
        return Focus(False, None, None, None, "nenhum patch com mais de 50% de tecido para medir o foco")
    p50, p90 = (float(np.percentile(laplacian, q)) for q in (50, 90))
    out_of_focus = float(np.mean(laplacian < FOCUS_RELATIVE * p90))
    warning = None
    if len(laplacian) < FOCUS_MIN_PATCHES:
        warning = f"{len(laplacian)} patches para o foco, abaixo de {FOCUS_MIN_PATCHES}: só alerta"
    blocked = material != "citologia" and warning is None and out_of_focus > FOCUS_BLOCK
    return Focus(blocked, out_of_focus, p50, p90, warning)
