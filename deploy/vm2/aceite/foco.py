"""Acceptance test 9, focus, on VM2 (skill pathsol-contrato-h5, "Testes de aceite"; plan, section 10.5).

Run by the operator on VM2, in the worker's test image built from the same
commit (it has tifffile), with the GPU, the pinned Hibou-L read-only, VM2's
identity, as 5433, and an empty work root on the temporary disk:

    docker run --rm --pull never --gpus all --user 5433:5433 --entrypoint python \
        -v <dir>/foco.py:/aceite/foco.py:ro \
        -v /data/modelos/hibou-L/31a3b9fee16554c8552cb643d311733bce8faf7c:/modelo:ro \
        -v /mnt/pathsol-aceite:/trabalho \
        pathsol-worker-teste:<commit> /aceite/foco.py --modelo /modelo --trabalho /trabalho \
        --container wsi-publico --blob <uuid>.svs --sha256 <the slide's sha256 in the database>

The sharp slide comes from its WSI container, sha256 checked, into a work
directory of this run under --trabalho, removed at the end even on failure.
A crop of level 0, with tissue and glass, becomes three Aperio-style SVS
copies on that disk only: the original, and two with a strong Gaussian blur
(Kohlberger 2019) on a fraction of the patches the focus rule counts, below
and well above 20%, chosen on the worker's own grid from the original's QC 2
rows. Each copy goes through the worker's Processor, with Hibou-L on the GPU
in fp16 and a local Blob: the .h5 or the scores file is written in the work
directory, and nothing goes to Azure. One JSON report goes to stdout; the
exit code is 0 only when the original and the copy below 20% end COMPLETED
with a .h5, and the copy above ends QC_FAILED "focus" with its scores file
and no .h5. What the operator can fix ends in one FALHA line instead.

Bounds: the work directory never passes MAX_WORK_BYTES, and at most two crops
are in memory at once (CROP_CELLS).
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
import uuid

import cv2
import h5py
import numpy as np
import openslide
import tifffile

from pathsol_worker import banco, blob, grid, passagem, qc
from pathsol_worker.slide import UnsupportedFormat, on_white, open_slide

# On VM2's temporary disk: the slide (v1 takes up to 10 GiB), then, with the
# slide gone, one copy at a time with its job (under 11 GiB at 0.1 µm/px).
MAX_WORK_BYTES = 12 * 1024**3
# 32 x 32 patches of level 0: 147 MiB of RGB at 0.5 µm/px and 3.6 GiB at the
# finest mpp the worker reads (0.1 µm/px), with at most two such arrays in memory.
CROP_CELLS = 32
# Half tissue and half glass, as on a slide: the copy's QC 1 thresholds its own
# thumbnail (Otsu), and a crop all in tissue would put the threshold inside the tissue.
TISSUE_TARGET = 0.5
# Strong at any mpp: 6 px at 0.5 µm/px, the strong blur of the worker's synthetic tests.
BLUR_UM = 3.0
SEED = 0
# The focus rule is the same for biopsies and specimens; cytology is never blocked.
MATERIAL = "peca"
# Copy, fraction of the patches the focus rule counts that is blurred, and the outcome expected.
VARIANTS = (
    ("original", 0.0, "COMPLETED"),
    ("abaixo", 0.10, "COMPLETED"),
    ("acima", 0.40, "QC_FAILED focus"),
)
# What each expected outcome leaves in slide-h5.
FILES = {"COMPLETED": ["h5"], "QC_FAILED focus": ["qc.h5"]}
# A slide is named by its UUID; a scanner's file name can carry the case number.
BLOB_NAME = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.svs"


class Refused(Exception):
    pass


def sha256_file(path):
    with open(path, "rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def reserve(work, need):
    """Refuses a step that would take the work directory past its ceiling."""
    used = sum(os.path.getsize(os.path.join(d, f)) for d, _, files in os.walk(work) for f in files)
    if used + need > MAX_WORK_BYTES:
        raise Refused(f"o diretório de trabalho passaria do teto de {MAX_WORK_BYTES} bytes: {used} usados e {need} pedidos")


def write_svs(path, image, mpp):
    """Aperio-style SVS, tiled and lossless, so that the blur is the copy's only change."""
    height, width = image.shape[:2]
    # Level 1 at the coarsest power of two not past QC 1's 4 µm/px: the level the worker reads its thumbnail from.
    factor = 2 ** int(math.log2(qc.QC1_MPP / mpp))
    level1 = cv2.resize(image, (width // factor, height // factor), interpolation=cv2.INTER_AREA)
    descriptions = (f"{width}x{height} [0,0 {width}x{height}] (256x256) RGB|MPP = {mpp}",
                    f"{width // factor}x{height // factor}")
    with tifffile.TiffWriter(path, bigtiff=True) as tif:
        for level, text in zip((image, level1), descriptions):
            tif.write(level, tile=(256, 256), photometric="rgb", compression="zlib",
                      description=f"Aperio Image Library v12.0.15\r\n{text}", metadata=None)


def blur_sigma(mpp):
    """The Gaussian's sigma in level-0 pixels: BLUR_UM at any mpp, as the worker reads every slide at 0.5 µm/px."""
    return BLUR_UM / mpp


def blurred(crop, cells, side, sigma):
    """A copy of the crop with each cell blurred, from the sharp pixels around it."""
    image = crop.copy()
    # Past the reach of OpenCV's kernel, so each cell comes out as if the whole crop were blurred.
    reach = math.ceil(4 * sigma)
    for x, y in cells:
        x0, y0 = max(x - reach, 0), max(y - reach, 0)
        region = cv2.GaussianBlur(crop[y0 : y + side + reach, x0 : x + side + reach], (0, 0), sigma)
        image[y : y + side, x : x + side] = region[y - y0 : y - y0 + side, x - x0 : x - x0 + side]
    return image


class Source(blob.Blob):
    """The WSI container, read with VM2's identity."""

    def size(self, container, name):
        with self._request("HEAD", container, name) as response:
            return int(response.headers["Content-Length"])


class LocalBlob:
    """The Processor's Blob on the work directory: nothing goes to Azure."""

    def __init__(self, copies, outdir):
        self.copies = copies
        self.outdir = outdir
        self.written = []

    def download(self, container, name, path, sha256):
        """Copies the local copy and checks its sha256, as the Blob does with a WSI."""
        shutil.copyfile(os.path.join(self.copies, name), path)
        if sha256_file(path) != sha256:
            raise blob.BlobError(f"{name}: o sha256 não é o do job")

    def upload(self, name, path, md5):
        target = os.path.join(self.outdir, name)
        os.makedirs(os.path.dirname(target), exist_ok=True)
        shutil.copyfile(path, target)
        self.written.append(name)


def tissue_window(mask, downsample, dimensions, size, side):
    """Top-left corner, on the worker's grid, of the crop closest to half tissue in QC 1, and that fraction."""
    width, height = dimensions
    # Corners from which the whole crop fits in the slide.
    corners = grid.coordinates(width - size + side, height - size + side, side)
    fractions = grid.cell_fractions(mask, downsample, corners, size)
    best = np.argmin(np.abs(fractions - TISSUE_TARGET))
    return corners[best], float(fractions[best])


def read_crop(path, corner, size, side):
    """The crop of level 0, read a strip of patches at a time."""
    x, y = (int(v) for v in corner)
    crop = np.empty((size, size, 3), dtype=np.uint8)
    with openslide.OpenSlide(path) as handle:
        for row in range(0, size, side):
            crop[row : row + side] = np.asarray(on_white(handle.read_region((x, y + row), 0, (size, side))))
    return crop


def through_worker(image, mpp, tenant, processor, local, work):
    """One copy as a job of the worker: (outcome, the files it left in slide-h5, their coordinates and QC 2 rows)."""
    # The SVS and its download in the job's directory, each under 1.5 times the pixels (deflate barely
    # grows them, level 1 adds a quarter at most), and the patches the job keeps; the slack covers the .h5.
    reserve(work, 3 * image.nbytes + CROP_CELLS**2 * passagem.PATCH_BYTES)
    slide = uuid.uuid4()
    name = f"{slide}.svs"
    path = os.path.join(local.copies, name)
    write_svs(path, image, mpp)
    job = banco.Job(uuid.uuid4(), tenant, slide, "local", name, sha256_file(path), None, MATERIAL, "HE", "RUNNING", 0)
    start = len(local.written)
    outcome = processor(job)
    os.remove(path)
    written = local.written[start:]
    if not written:
        return outcome, written, np.empty((0, 2), dtype=np.int32), np.empty((0, 3), dtype=np.float32)
    with h5py.File(os.path.join(local.outdir, written[0]), "r") as f:
        return outcome, written, f["coordinates"][:], f["qc_scores"][:]


def outcome_text(outcome):
    """The final state, with the reason when there is one, as in "QC_FAILED focus"."""
    reason = getattr(outcome, "reason", None)
    return f"{outcome.state} {reason}" if reason else outcome.state


def entry(label, planned, blurred_patches, expected, outcome, written, scores):
    result = outcome_text(outcome)
    # None with nothing to measure, as when the worker left no file with the QC 2 scores.
    out_of_focus = qc.focus(scores, MATERIAL).out_of_focus
    return {
        "copia": label,
        "fracao_planejada": planned,
        "patches_borrados": blurred_patches,
        "patches_extraidos": len(scores),
        "patches_do_foco": int((scores[:, 0] > qc.FOCUS_TISSUE).sum()),
        "fracao_fora_de_foco": None if out_of_focus is None else round(out_of_focus, 4),
        "resultado": result,
        "esperado": expected,
        "arquivos": written,
        "confere": result == expected and [name.split(".", 1)[1] for name in written] == FILES[expected],
    }


def run(source, container, name, sha256, root, extractor, version, software, workers=3):
    """Test 9 in a work directory of its own under root, removed at the end even on failure; returns the report."""
    # Imported here: the QC 2 processes are spawned with this script as their main module, and must not import torch.
    from pathsol_worker import processo

    # Emptied at the end of every run, so anything in it was left by another one: never removed here.
    if os.listdir(root):
        raise Refused(f"{root} não está vazio")
    work = tempfile.mkdtemp(prefix="foco-", dir=root)
    try:
        reserve(work, source.size(container, name))
        path = os.path.join(work, name)
        source.download(container, name, path, sha256)
        with open_slide(path) as s:
            mask, downsample, _, _ = qc.thumbnail_mask(s)
            mpp, dimensions = s.mpp, s.dimensions
        side = grid.side_level0(mpp)
        size = CROP_CELLS * side
        corner, tissue = tissue_window(mask, downsample, dimensions, size, side)
        crop = read_crop(path, corner, size, side)
        os.remove(path)

        local = LocalBlob(os.path.join(work, "copias"), os.path.join(work, "slide-h5"))
        os.mkdir(local.copies)
        processor = processo.Processor(local, extractor, version, software, os.path.join(work, "jobs"), workers)
        tenant = uuid.uuid4()
        copies, order = [], np.empty((0, 2), dtype=np.int32)
        for label, planned, expected in VARIANTS:
            cells = order[: round(planned * len(order))]
            outcome, written, coordinates, scores = through_worker(blurred(crop, cells, side, blur_sigma(mpp)), mpp,
                                                                   tenant, processor, local, work)
            if label == "original":
                # The patches the focus rule counts in the original, in a fixed random order.
                order = np.random.default_rng(SEED).permutation(coordinates[scores[:, 0] > qc.FOCUS_TISSUE])
                if len(order) < qc.FOCUS_MIN_PATCHES:
                    raise Refused(f"a cópia original terminou em {outcome_text(outcome)} com {len(order)} patches para "
                                  f"a regra do foco, que só bloqueia a partir de {qc.FOCUS_MIN_PATCHES}: escolha outra lâmina")
            copies.append(entry(label, planned, len(cells), expected, outcome, written, scores))
        return {
            "lamina": {"blob": f"{container}/{name}", "mpp": mpp, "dimensoes": list(dimensions)},
            "recorte": {"origem": [int(v) for v in corner], "lado_px": size, "patches": CROP_CELLS**2,
                        "fracao_tecido_qc1": round(tissue, 3)},
            "borrao_sigma_um": BLUR_UM,
            "copias": copies,
            "veredito": "OK" if all(copy["confere"] for copy in copies) else "FALHA",
        }
    finally:
        shutil.rmtree(work)


def blob_name(value):
    if not re.fullmatch(BLOB_NAME, value):
        raise argparse.ArgumentTypeError("o blob precisa ser UUID.svs")
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description="Teste de aceite 9 (foco) na VM2.")
    parser.add_argument("--modelo", required=True, help="diretório da revisão fixada do Hibou-L, só para leitura")
    parser.add_argument("--trabalho", required=True, help="raiz vazia do diretório de trabalho, no disco temporário da VM2")
    parser.add_argument("--container", required=True, choices=("wsi-publico",))
    parser.add_argument("--blob", required=True, type=blob_name)
    parser.add_argument("--sha256", required=True)
    args = parser.parse_args(argv)
    # Imported here for the reason in run().
    from pathsol_worker import extractor, versao

    try:
        report = run(Source(), args.container, args.blob, args.sha256, args.trabalho,
                     extractor.Extractor(args.modelo, "cuda", "fp16"), versao.extractor_version(args.modelo),
                     versao.software())
    except (Refused, blob.BlobError, UnsupportedFormat, OSError) as error:
        print(f"FALHA: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["veredito"] == "OK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
