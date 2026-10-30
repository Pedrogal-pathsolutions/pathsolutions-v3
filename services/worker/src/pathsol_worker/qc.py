"""Tissue and focus metrics (plan, sections 10.4 and 10.5).

Tissue is saturation above a per-slide Otsu threshold, which never drops below
a floor, so blank glass and its noise read as no tissue. Focus is measured on
the luminance, only where tissue surrounds the pixel: the 3 x 3 kernels at the
tissue border would otherwise also see the glass.
"""
import cv2
import numpy as np

# Provisional until calibrated on the acceptance slides; part of qc_version.
MIN_SATURATION = 15
FOCUS_NEIGHBOURHOOD = np.ones((3, 3), dtype=np.uint8)


def saturation(rgb):
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1]


def tissue_threshold(thumb_rgb):
    otsu, _ = cv2.threshold(saturation(thumb_rgb), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return max(int(otsu), MIN_SATURATION)


def tissue_mask(rgb, threshold):
    return saturation(rgb) > threshold


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
