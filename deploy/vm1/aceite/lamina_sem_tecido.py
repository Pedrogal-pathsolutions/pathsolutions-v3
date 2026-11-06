"""Synthetic slide of empty glass for test 5 of the worker (skill pathsol-contrato-h5; plan, section 17).

The lab's blank slide has not arrived (Pedro, 06/11/2026): test 5 runs first
on this one, which goes to the storage like the public slides, through
pathsol_enviar_lamina.py, and the real one repeats the test later. It is an
Aperio-style SVS at 40x (0.25 µm/px) of 3 x 2 mm of glass: level 0, a
stripped thumbnail, then the 4x and 16x levels. No label and no macro; the
descriptions carry only the header, AppMag and MPP. About 135 MiB. It is
written under a partial name and takes a fresh UUID name, which it prints,
only once whole; an existing file is never replaced.

Runs on VM1 in the worker test image (tifffile is a dev dependency there), as the operator's user:

    docker run --rm --network none --user "$(id -u):$(id -g)" -v /data/staging/aceite:/data/staging/aceite \
        -v "$PWD/deploy/vm1/aceite:/aceite:ro" --entrypoint python pathsol-worker-teste:<tag> \
        /aceite/lamina_sem_tecido.py /data/staging/aceite
"""
import os
import sys
import uuid

import cv2
import numpy as np
import tifffile

MPP = 0.25
APP_MAG = 40
DEFAULT_MM = (3, 2)
# 16 x 0.25 µm/px is the 4 µm/px level that QC 1 reads its thumbnail from.
DOWNSAMPLES = (1, 4, 16)
TILE = 256
# Glass under a brightfield scanner: near white with a faint blue cast, a few
# levels darker towards one corner, and sensor noise of about 2 levels.
GLASS = np.array((239, 240, 242), dtype=np.float32)
SHADING = 6
NOISE = 2.0
ROWS = 512


def glass(height, width):
    """Level 0, a band of rows at a time, so that only the image itself is held in memory."""
    rng = np.random.default_rng(0)  # a fixed seed: the same image always writes the same file
    across = np.linspace(0, SHADING / 2, width, dtype=np.float32)
    down = np.linspace(0, SHADING / 2, height, dtype=np.float32)
    image = np.empty((height, width, 3), dtype=np.uint8)
    for top in range(0, height, ROWS):
        shade = (down[top:top + ROWS, None] + across)[..., None]
        noise = rng.standard_normal((*shade.shape[:2], 3), dtype=np.float32) * NOISE
        image[top:top + ROWS] = np.clip(np.rint(GLASS - shade + noise), 0, 255)
    return image


def write_svs(f, size_mm):
    width, height = (round(mm * 1000 / MPP) for mm in size_mm)
    level0 = glass(height, width)
    levels = [cv2.resize(level0, (width // d, height // d), interpolation=cv2.INTER_AREA) for d in DOWNSAMPLES[1:]]
    head = f"Aperio Image Library v12.0.15\r\n{width}x{height} [0,0 {width}x{height}] ({TILE}x{TILE})"
    fields = f"|AppMag = {APP_MAG}|MPP = {MPP}"
    # Aperio's layout: level 0, a stripped thumbnail (desidentificar.py keeps it), then the other levels.
    with tifffile.TiffWriter(f) as tif:
        for image, tiled in ((level0, True), (levels[-1], False), *((level, True) for level in levels)):
            reduced = "" if image is level0 else f" -> {image.shape[1]}x{image.shape[0]}"
            tif.write(image, tile=(TILE, TILE) if tiled else None, photometric="rgb", compression="zlib",
                      description=f"{head}{reduced} RGB{fields}", metadata=None)


def stage(directory, size_mm=DEFAULT_MM):
    """Writes the slide in directory under a fresh UUID name, which appears only once the file is whole."""
    path = os.path.join(directory, f"{uuid.uuid4()}.svs")
    partial = f"{path}.parcial"
    with open(partial, "xb") as f:
        try:
            write_svs(f, size_mm)
            f.flush()
            os.fsync(f.fileno())
            os.link(partial, path)  # unlike a rename, a link never replaces an existing file
        finally:
            os.remove(partial)
    return path


def main(directory):
    try:
        path = stage(directory)
    except OSError as error:
        print(f"FALHA: {error}", file=sys.stderr)
        return 1
    width, height = DEFAULT_MM
    print(f"OK {path}: vidro sem tecido, {width} x {height} mm a {MPP} µm/px, {os.path.getsize(path)} bytes")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("uso: lamina_sem_tecido.py DIRETORIO")
    sys.exit(main(sys.argv[1]))
