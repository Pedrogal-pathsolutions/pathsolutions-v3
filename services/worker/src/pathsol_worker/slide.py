"""Opens a WSI with OpenSlide and lets out only allowlisted values (plan, section 4.1).

Label, macro and the header are never read here: they can carry the barcode
or the case number. A refusal carries the reason the lab sees.
"""
import math
import os

import numpy as np
import openslide
from PIL import Image

from pathsol_worker.grid import PATCH

MPP_MIN = 0.1
MPP_MAX = 0.55
MPP_XY_TOLERANCE = 0.01
# The level read for the thumbnail must be small: level 0 is never read whole.
MAX_THUMBNAIL_SOURCE_PIXELS = 200_000_000
# 40x scans state mpp a bit above 0.25, so their 16x level sits just above
# 4 um/px; it still counts as the target's level.
THUMBNAIL_LEVEL_TOLERANCE = 1.05

UNSUPPORTED = "formato não suportado"
NO_SCALE = "escala indisponível"


class UnsupportedFormat(Exception):
    """Terminal state "formato não suportado"; reason is what the lab sees, detail is for the operator."""

    def __init__(self, reason, detail):
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def checked_mpp(x, y):
    try:
        mpp_x, mpp_y = float(x), float(y)
    except (TypeError, ValueError):
        raise UnsupportedFormat(NO_SCALE, "mpp ausente ou ilegível") from None
    if not all(math.isfinite(v) and MPP_MIN <= v <= MPP_MAX for v in (mpp_x, mpp_y)):
        raise UnsupportedFormat(NO_SCALE, f"mpp fora da faixa de {MPP_MIN} a {MPP_MAX} µm/px")
    if abs(mpp_x - mpp_y) > MPP_XY_TOLERANCE * max(mpp_x, mpp_y):
        raise UnsupportedFormat(NO_SCALE, "mpp x e y diferem mais de 1%")
    return (mpp_x + mpp_y) / 2


def on_white(region):
    """Unscanned area (transparent in OpenSlide) becomes white glass."""
    white = Image.new("RGBA", region.size, (255, 255, 255, 255))
    return Image.alpha_composite(white, region).convert("RGB")


def open_slide(path):
    if os.path.splitext(path)[1].lower() != ".svs":
        raise UnsupportedFormat(UNSUPPORTED, "extensão diferente de .svs")
    if openslide.OpenSlide.detect_format(path) != "aperio":
        raise UnsupportedFormat(UNSUPPORTED, "o leitor não reconhece um SVS da Aperio")
    try:
        handle = openslide.OpenSlide(path)
    except openslide.OpenSlideError as error:
        raise UnsupportedFormat(UNSUPPORTED, "o leitor não abre o arquivo") from error
    try:
        return Slide(handle)
    except BaseException:
        handle.close()
        raise


class Slide:
    def __init__(self, handle):
        self._handle = handle
        self.level_count = handle.level_count
        if self.level_count < 2:
            raise UnsupportedFormat(UNSUPPORTED, "sem pirâmide")
        properties = handle.properties
        self.mpp = checked_mpp(
            properties.get(openslide.PROPERTY_NAME_MPP_X), properties.get(openslide.PROPERTY_NAME_MPP_Y)
        )
        self.mpp_source = "openslide.mpp-x/mpp-y"
        self.dimensions = handle.dimensions
        self.level_dimensions = handle.level_dimensions
        self.level_downsamples = handle.level_downsamples
        self.reader = f"openslide {openslide.__library_version__} (openslide-python {openslide.__version__})"

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        self._handle.close()

    def read_patch(self, x, y, side):
        """The level-0 square of the given side at (x, y), resampled to 224 x 224 RGB."""
        region = self._handle.read_region((int(x), int(y)), 0, (side, side))
        return on_white(region).resize((PATCH, PATCH), Image.BICUBIC)

    def thumbnail(self, target_mpp):
        """The whole slide at target_mpp: (RGB array, level-0 pixels per thumbnail pixel).

        Read from the coarsest level not coarser than the target, or else from
        the finest one up to twice the target, among the levels under the cap.
        """
        level_mpp = [self.mpp * d for d in self.level_downsamples]
        usable = [
            level
            for level, (width, height) in enumerate(self.level_dimensions)
            if width * height <= MAX_THUMBNAIL_SOURCE_PIXELS and level_mpp[level] <= 2 * target_mpp
        ]
        if not usable:
            raise UnsupportedFormat(UNSUPPORTED, "a pirâmide não tem nível para a miniatura")
        finer = [level for level in usable if level_mpp[level] <= THUMBNAIL_LEVEL_TOLERANCE * target_mpp]
        level = max(finer, key=level_mpp.__getitem__) if finer else min(usable, key=level_mpp.__getitem__)
        downsample = target_mpp / self.mpp
        width, height = self.level_dimensions[level]
        region = self._handle.read_region((0, 0), level, (width, height))
        size = (max(1, round(self.dimensions[0] / downsample)), max(1, round(self.dimensions[1] / downsample)))
        return np.asarray(on_white(region).resize(size, Image.BICUBIC)), self.dimensions[0] / size[0]
