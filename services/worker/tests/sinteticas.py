"""Synthetic Aperio-style SVS files for the tests; no real slide is used."""
import numpy as np
import tifffile


def aperio_description(width, height, mpp, extra=""):
    mpp_field = "" if mpp is None else f"|MPP = {mpp}"
    return f"Aperio Image Library v12.0.15\r\n{width}x{height} [0,0 {width}x{height}] (256x256) RGB|AppMag = 40{mpp_field}{extra}"


def write_svs(path, image, mpp=0.25, downsamples=(1, 4), extra="", description=None):
    """Tiled pyramid, one IFD per level, deflate tiles (decoded by libtiff in OpenSlide)."""
    height, width = image.shape[:2]
    with tifffile.TiffWriter(path) as tif:
        for index, factor in enumerate(downsamples):
            level = image[::factor, ::factor]
            text = description if description is not None else aperio_description(width, height, mpp, extra)
            tif.write(
                np.ascontiguousarray(level),
                tile=(256, 256),
                photometric="rgb",
                compression="zlib",
                description=text if index == 0 else f"Aperio Image Library v12.0.15\r\n{level.shape[1]}x{level.shape[0]}",
                metadata=None,
            )


def tissue_image(width=2048, height=1024):
    """White glass with a pink block in the left half (tissue) and blue ink in a corner."""
    image = np.full((height, width, 3), 240, dtype=np.uint8)
    image[: height // 2 + 256, : width // 2] = (200, 120, 170)
    image[-128:, -128:] = (40, 60, 200)
    return image
