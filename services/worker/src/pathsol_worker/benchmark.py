"""Worker benchmark on VM2 (plan, section 8.4; Phase 4, slice 1).

Measures Hibou-L throughput on the GPU by precision and batch size, the CPU
side (reading, resampling and QC 2) with 1 to 3 processes, each slide end to
end in fp16, and fp16 against fp32 on the first real patches of each slide.
Writes one JSON with the numbers and the versions; of a slide, only its
public file name.

    python -m pathsol_worker.benchmark --modelo DIR --saida OUT.json SLIDE.svs ...
"""
import argparse
import copy
import datetime
import json
import os
import subprocess
import time

import cv2
import numpy as np
import openslide
import PIL
import torch
import transformers

from pathsol_worker import grid, patches, qc
from pathsol_worker.extractor import Extractor
from pathsol_worker.slide import open_slide

BATCHES = (32, 64, 128, 256)
GPU_SECONDS = 10
COSINE_SAMPLE = 256


def now():
    return datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds")


def row_cosine(a, b):
    a, b = a.astype(np.float64), b.astype(np.float64)
    return (a * b).sum(axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))


def versions():
    try:
        driver = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=30,
        ).stdout.strip()
    except OSError:
        driver = None
    return {
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "transformers": transformers.__version__,
        "pillow": PIL.__version__,
        "numpy": np.__version__,
        "opencv": cv2.__version__,
        "openslide": openslide.__library_version__,
        "gpu": torch.cuda.get_device_name(0),
        "driver": driver,
        "cpus": os.cpu_count(),
    }


def gpu_throughput(ex, batch, seconds=GPU_SECONDS):
    """Patches per second of embed(): upload, normalization, model and download."""
    fake = np.random.default_rng(0).integers(0, 256, (batch, 224, 224, 3), dtype=np.uint8)
    try:
        ex.embed(fake)
        torch.cuda.reset_peak_memory_stats()
        done, start = 0, time.perf_counter()
        while time.perf_counter() - start < seconds:
            ex.embed(fake)
            done += batch
        elapsed = time.perf_counter() - start
    except torch.cuda.OutOfMemoryError:
        torch.cuda.empty_cache()
        return {"lote": batch, "erro": "sem memória"}
    return {
        "lote": batch,
        "patches_s": round(done / elapsed, 1),
        "memoria_gib": round(torch.cuda.max_memory_allocated() / 2**30, 2),
    }


def bench_slide(path, fp16, fp32, batch, workers=3, cpu_workers=(1, 2, 3), sample=600):
    start = time.perf_counter()
    with open_slide(path) as s:
        mask, downsample, threshold = qc.thumbnail_mask(s)
        side, cells = grid.candidates(s.dimensions, s.mpp, mask, downsample)
        result = {
            "arquivo": os.path.basename(path),
            "dimensoes": list(s.dimensions),
            "mpp": s.mpp,
            "niveis": s.level_count,
            "lado_nivel0": side,
            "candidatos": len(cells),
        }
    result["mascara_s"] = round(time.perf_counter() - start, 2)

    probe = cells[:: max(1, len(cells) // sample)][:sample]
    result["cpu"] = []
    for n in cpu_workers:
        t = time.perf_counter()
        count = sum(1 for _ in patches.read_patches(path, probe, side, threshold, n))
        result["cpu"].append({"processos": n, "patches_s": round(count / (time.perf_counter() - t), 1)})

    extracted = rejected = 0
    gpu_busy = 0.0
    pending, kept, kept16 = [], [], []

    def flush():
        nonlocal extracted, gpu_busy
        t = time.perf_counter()
        out = fp16.embed(np.stack(pending))
        gpu_busy += time.perf_counter() - t
        missing = COSINE_SAMPLE - len(kept)
        if missing > 0:
            kept.extend(pending[:missing])
            kept16.append(out[:missing])
        extracted += len(pending)
        pending.clear()

    t = time.perf_counter()
    for patch, (fraction, _, _) in patches.read_patches(path, cells, side, threshold, workers):
        if fraction < qc.EXTRACTION_FLOOR:
            rejected += 1
            continue
        pending.append(patch)
        if len(pending) == batch:
            flush()
    if pending:
        flush()
    elapsed = time.perf_counter() - t
    result.update(
        extraidos=extracted,
        rejeitados=rejected,
        extracao_s=round(elapsed, 2),
        ponta_a_ponta_s=round(result["mascara_s"] + elapsed, 2),
        patches_s=round(extracted / elapsed, 1) if elapsed else None,
        gpu_ocupada=round(gpu_busy / elapsed, 3) if elapsed else None,
    )

    if kept:
        a = np.concatenate(kept16)
        b = np.concatenate([fp32.embed(np.stack(kept[i : i + batch])) for i in range(0, len(kept), batch)])
        bad = not (np.isfinite(a).all() and np.isfinite(b).all())
        cosine = None if bad else row_cosine(a, b)
        result["cosseno_fp16_fp32"] = {
            "n": len(kept),
            "media": None if bad else float(cosine.mean()),
            "minimo": None if bad else float(cosine.min()),
            "nan_inf": bad,
        }
    return result


def write(result, path):
    partial = path + ".parcial"
    with open(partial, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(partial, path)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Benchmark do worker na VM2 (Fase 4, fatia 1).")
    parser.add_argument("--modelo", required=True, help="diretório da revisão fixada do Hibou-L")
    parser.add_argument("--saida", required=True)
    parser.add_argument("laminas", nargs="+")
    args = parser.parse_args(argv)

    result = {"inicio_utc": now(), "carga": {}, "gpu": {}, "laminas": []}
    t = time.perf_counter()
    torch.zeros(1, device="cuda")
    result["carga"]["cuda_s"] = round(time.perf_counter() - t, 2)
    t = time.perf_counter()
    fp16 = Extractor(args.modelo, "cuda", "fp16")
    result["carga"]["modelo_s"] = round(time.perf_counter() - t, 2)
    result["carga"]["modelo_pronto_utc"] = now()
    # Same weights; only the autocast differs.
    fp32 = copy.copy(fp16)
    fp32.fp16 = False
    result["versoes"] = versions()

    for name, ex in (("fp16", fp16), ("fp32", fp32)):
        result["gpu"][name] = [gpu_throughput(ex, b) for b in BATCHES]
        write(result, args.saida)
    batch = max((r for r in result["gpu"]["fp16"] if "patches_s" in r), key=lambda r: r["patches_s"])["lote"]
    result["lote_usado"] = batch
    for path in args.laminas:
        result["laminas"].append(bench_slide(path, fp16, fp32, batch))
        write(result, args.saida)
    result["fim_utc"] = now()
    write(result, args.saida)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
