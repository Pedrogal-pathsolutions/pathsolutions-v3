"""Acceptance tests 1 and 6 of the worker, on VM2 (skill pathsol-contrato-h5; plan, section 17).

    comparar --h5 NAME_A --h5 NAME_B
        Test 1: two .h5 of one slide, from two jobs, in slide-h5. Same tenant,
        slide and extractor_version; the same set of patch coordinates; and the
        cosine of the embeddings matched by coordinate with mean >= 0.999, with
        no NaN or Inf. One JSON line with the numbers; exit 0 only for OK.
    grade --h5 NAME --lamina wsi-<tenant>/<uuid>.svs --sha256 HEX --saida FILE.png
        Test 6, the simple check of Phase 4: every patch square of the .h5 over
        a thumbnail of the slide's pyramid, at most 2048 px on the long side, for
        Pedro to look at. The worker's reader opens the slide, so the label and
        the macro are never read. One JSON line with the counts.

Runs in the worker image with VM2's identity, as 5433, with a host directory
at /trabalho (and one at /saida for the PNG):

    docker run --rm --pull never --user 5433:5433 --entrypoint python \
        -v <dir>/aceite_worker.py:/aceite/aceite_worker.py:ro -v /mnt/pathsol-aceite:/trabalho \
        pathsol-worker:<commit> /aceite/aceite_worker.py comparar --h5 ... --h5 ...

The work directory must start empty. The blobs' sizes, from a HEAD, are
checked against a cap and a free-disk margin before any download; the blobs
go to a fresh directory inside it, removed at the end, even on failure. The
WSI is checked by the sha256 given (the database's), each .h5 by the MD5 the
worker committed it with.
"""
import argparse
import base64
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile

import h5py
import numpy as np
from PIL import Image, ImageDraw

from pathsol_worker import blob, mensagem
from pathsol_worker.slide import UnsupportedFormat, open_slide

WORK = "/trabalho"
# Room for the largest WSI of v1 (10 GiB, skill pathsol-contrato-h5) and its .h5.
MAX_WORK_BYTES = 12 * 1024**3
# The worker keeps the same margin free on the temporary disk.
FREE_MARGIN = 2 * 1024**3
# Skill pathsol-contrato-h5, test 1.
MIN_MEAN_COSINE = 0.999
# At most this many coordinates of each side of a different set go in the output.
EXAMPLES = 10
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
# <tenant>/<slide>/<12 hex of the extractor_version>/<job>.h5, as the worker names it.
H5_NAME = re.compile(rf"{UUID}/{UUID}/[0-9a-f]{{12}}/{UUID}\.h5")
PNG_MAX_SIDE = 2048
# Semi-transparent, so the tissue under each square stays visible.
FILL = (0, 255, 0, 48)
OUTLINE = (0, 128, 0, 160)


class Refused(Exception):
    pass


class Storage(blob.Blob):
    """The worker's Blob client, plus a HEAD and a GET checked by the MD5 the worker committed with the .h5."""

    def head(self, container, name):
        with self._request("HEAD", container, name) as response:
            return int(response.headers["Content-Length"]), response.headers.get("Content-MD5")

    def fetch(self, container, name, path, md5):
        digest = hashlib.md5()
        with self._request("GET", container, name) as response, open(path, "wb") as out:
            for chunk in iter(lambda: response.read(blob.BLOCK), b""):
                digest.update(chunk)
                out.write(chunk)
        if base64.b64encode(digest.digest()).decode() != md5:
            raise blob.BlobError(f"{container}/{name}: o MD5 não é o do blob")


def h5_name(text):
    if not H5_NAME.fullmatch(text):
        raise argparse.ArgumentTypeError("esperado <tenant>/<lâmina>/<versão>/<job>.h5 do slide-h5")
    return text


def wsi_blob(text):
    """(container, name) of a WSI, as the job message names it."""
    match = mensagem.BLOB.fullmatch(text)
    if match is None:
        raise argparse.ArgumentTypeError("esperado wsi-<tenant>/<uuid da lâmina>.svs")
    return match.groups()


def sha256_hex(text):
    if not re.fullmatch(r"[0-9a-f]{64}", text):
        raise argparse.ArgumentTypeError("esperado o sha256 em 64 hexadecimais minúsculos")
    return text


def check_room(storage, blobs):
    """(size, MD5) of each (container, name) by HEAD; refused before any download when the blobs
    would pass the cap or leave the disk without its margin."""
    # Emptied at the end, so anything in it was left by another run: never removed here.
    if os.listdir(WORK):
        raise Refused(f"{WORK} não está vazio")
    found = [storage.head(container, name) for container, name in blobs]
    need = sum(size for size, _ in found)
    if need > MAX_WORK_BYTES:
        raise Refused(f"os blobs somam {need} bytes, acima do teto de {MAX_WORK_BYTES} do diretório de trabalho")
    if shutil.disk_usage(WORK).free - need < FREE_MARGIN:
        raise Refused(f"o disco ficaria com menos de {FREE_MARGIN} bytes livres")
    return found


def row_cosine(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    # A row with NaN or Inf gives NaN; compare reports it apart.
    with np.errstate(divide="ignore", invalid="ignore"):
        return (a * b).sum(axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))


def read_h5(path):
    with h5py.File(path, "r") as f:
        attrs = {key: f.attrs[key] for key in ("tenant_id", "slide_id", "extractor_version")}
        return attrs, f["coordinates"][:], f["embeddings"][:]


def compare(path_a, path_b):
    """Test 1 on two downloaded .h5: the numbers and the verdict."""
    (attrs_a, coords_a, emb_a), (attrs_b, coords_b, emb_b) = read_h5(path_a), read_h5(path_b)
    same_slide = (attrs_a["tenant_id"], attrs_a["slide_id"]) == (attrs_b["tenant_id"], attrs_b["slide_id"])
    same_version = attrs_a["extractor_version"] == attrs_b["extractor_version"]
    # Rows are matched by coordinate, whatever their order in each file.
    rows_b = {xy: i for i, xy in enumerate(map(tuple, coords_b.tolist()))}
    keys_a = list(map(tuple, coords_a.tolist()))
    pairs = np.array([(i, rows_b[xy]) for i, xy in enumerate(keys_a) if xy in rows_b], dtype=np.int64).reshape(-1, 2)
    only_a = sorted(set(keys_a) - rows_b.keys())
    only_b = sorted(rows_b.keys() - set(keys_a))
    cosine = row_cosine(emb_a[pairs[:, 0]], emb_b[pairs[:, 1]])
    finite = bool(np.isfinite(emb_a).all() and np.isfinite(emb_b).all() and np.isfinite(cosine).all())
    mean, minimum = (float(cosine.mean()), float(cosine.min())) if finite and len(cosine) else (None, None)
    passed = (same_slide and same_version and not only_a and not only_b
              and mean is not None and mean >= MIN_MEAN_COSINE)
    return {
        "mesma_lamina": same_slide,
        "mesmo_extractor_version": same_version,
        "patches": [len(coords_a), len(coords_b)],
        "comuns": len(pairs),
        "so_no_primeiro": len(only_a),
        "so_no_segundo": len(only_b),
        "exemplos_so_no_primeiro": only_a[:EXAMPLES],
        "exemplos_so_no_segundo": only_b[:EXAMPLES],
        "cosseno": {"media": mean, "minimo": minimum, "nan_inf": not finite},
        "veredito": "OK" if passed else "FALHA",
    }


def compare_command(args, storage):
    if len(args.h5) != 2 or args.h5[0] == args.h5[1]:
        raise Refused("comparar pede duas .h5 diferentes")
    found = check_room(storage, [(blob.H5_CONTAINER, name) for name in args.h5])
    with tempfile.TemporaryDirectory(dir=WORK) as work:
        paths = [os.path.join(work, f"{i}.h5") for i in range(2)]
        for name, (_, md5), path in zip(args.h5, found, paths):
            storage.fetch(blob.H5_CONTAINER, name, path, md5)
        return {"h5": args.h5, **compare(*paths)}


def draw(thumb, coords, side, per_pixel):
    """Every patch square over the thumbnail; per_pixel is level-0 pixels per thumbnail pixel."""
    image = Image.fromarray(thumb).convert("RGBA")
    overlay = Image.new("RGBA", image.size)
    pen = ImageDraw.Draw(overlay)
    for x, y in coords.tolist():
        pen.rectangle((math.floor(x / per_pixel), math.floor(y / per_pixel),
                       math.ceil((x + side) / per_pixel) - 1, math.ceil((y + side) / per_pixel) - 1),
                      fill=FILL, outline=OUTLINE)
    return Image.alpha_composite(image, overlay).convert("RGB")


def grid_command(args, storage):
    container, name = args.lamina
    _, (_, md5) = check_room(storage, [(container, name), (blob.H5_CONTAINER, args.h5)])
    with tempfile.TemporaryDirectory(dir=WORK) as work:
        # The worker's reader goes by the extension: the WSI keeps its blob name, <uuid>.svs.
        h5_path, wsi = os.path.join(work, "grade.h5"), os.path.join(work, name)
        storage.fetch(blob.H5_CONTAINER, args.h5, h5_path, md5)
        with h5py.File(h5_path, "r") as f:
            coords, side, rejected = f["coordinates"][:], int(f.attrs["tile_size"]), int(f.attrs["n_rejected"])
            source = f.attrs["wsi_sha256"]
        # Checked before the WSI's download, the larger of the two.
        if source != args.sha256:
            raise Refused("o .h5 é de outra WSI: o wsi_sha256 dele não é o da lâmina")
        storage.download(container, name, wsi, args.sha256)
        with open_slide(wsi) as s:
            # A slide smaller than the PNG is drawn at level 0, never enlarged.
            thumb, per_pixel = s.thumbnail(s.mpp * max(1.0, max(s.dimensions) / PNG_MAX_SIDE))
    image = draw(thumb, coords, side, per_pixel)
    image.save(args.saida, format="PNG")
    return {"h5": args.h5, "lamina": f"{container}/{name}", "patches": len(coords), "lado_nivel0": side,
            "abaixo_do_piso": rejected, "png": args.saida, "png_dimensoes": list(image.size)}


def main(argv=None, storage=None):
    parser = argparse.ArgumentParser(description="Testes de aceite 1 e 6 do worker, na VM2.")
    commands = parser.add_subparsers(required=True)
    comparar = commands.add_parser("comparar", help="teste 1: a mesma lâmina processada duas vezes")
    comparar.add_argument("--h5", required=True, action="append", type=h5_name, help="blob no slide-h5; duas vezes")
    comparar.set_defaults(run=compare_command)
    grade = commands.add_parser("grade", help="teste 6: PNG da grade de patches sobre a miniatura")
    grade.add_argument("--h5", required=True, type=h5_name, help="blob no slide-h5")
    grade.add_argument("--lamina", required=True, type=wsi_blob, help="wsi-<tenant>/<uuid da lâmina>.svs")
    grade.add_argument("--sha256", required=True, type=sha256_hex, help="sha256 da WSI no banco")
    grade.add_argument("--saida", required=True, help="arquivo PNG")
    grade.set_defaults(run=grid_command)
    args = parser.parse_args(argv)
    try:
        result = args.run(args, storage or Storage())
    except (Refused, blob.BlobError, UnsupportedFormat, OSError) as error:
        print(f"FALHA: {error}", file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result.get("veredito") == "FALHA" else 0


if __name__ == "__main__":
    sys.exit(main())
