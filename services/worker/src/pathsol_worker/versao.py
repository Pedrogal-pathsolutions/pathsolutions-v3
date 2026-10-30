"""extractor_version and qc_version (skill pathsol-contrato-h5; plan, section 10.2).

Canonical JSON strings: sorted keys, no spaces. The extractor_version carries
the sha256 of the weights, the configurations and the model's code, so a
change in any of them is another version; its short hash goes in the blob path.
"""
import hashlib
import json
import os
import subprocess

import PIL
import torch
import transformers

from pathsol_worker import extractor, grid, qc

MODEL = "histai/hibou-L@31a3b9fee16554c8552cb643d311733bce8faf7c"
MODEL_FILES = ("config.json", "configuration_dinov2.py", "model.safetensors", "modeling_dinov2.py", "preprocessor_config.json")


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extractor_version(model_dir):
    return canonical({
        "modelo": MODEL,
        "arquivos": {name: sha256_file(os.path.join(model_dir, name)) for name in MODEL_FILES},
        "preprocessamento": {
            "cor": "RGB",
            "reamostragem": "lado round(224 x 0,5 / mpp) do nível 0 para 224 x 224, bicúbico do Pillow com antialias",
            "media": list(extractor.MEAN),
            "desvio": list(extractor.STD),
        },
        "normalizacao": "none",
        "token": "CLS (pooler_output), sem os registradores",
        "patch": grid.PATCH,
        "stride": grid.PATCH,
        "mpp": grid.TARGET_MPP,
        "precisao": "fp16 por torch.autocast, saída em float32",
        "atencao": extractor.ATTENTION,
    })


def short_hash(version):
    return hashlib.sha256(version.encode()).hexdigest()[:12]


def software():
    """Versions in the .h5 attrs: changing any of them asks for the regression (cosine >= 0.999)."""
    try:
        driver = subprocess.run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                                capture_output=True, text=True, timeout=30).stdout.strip() or None
    except OSError:
        driver = None
    return {
        "torch": torch.__version__,
        "transformers": transformers.__version__,
        "cuda": torch.version.cuda,
        "pillow": PIL.__version__,
        "driver": driver,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    }


def qc_version():
    return canonical({
        "saturacao_minima": qc.MIN_SATURATION,
        "caneta": {"matizes": qc.PEN_HUES, "saturacao_minima": qc.PEN_MIN_SATURATION, "valor_maximo": qc.PEN_MAX_VALUE},
        "miniatura_mpp": qc.QC1_MPP,
        "morfologia_um": qc.MORPHOLOGY_UM,
        "fragmento_minimo_um2": qc.MIN_FRAGMENT_UM2,
        "vidro_vazio_mm2": qc.EMPTY_MM2,
        "tecido_minimo_mm2": qc.MIN_TISSUE_MM2,
        "piso_extracao": qc.EXTRACTION_FLOOR,
        "foco": {
            "tecido": qc.FOCUS_TISSUE,
            "relativo_p90": qc.FOCUS_RELATIVE,
            "bloqueio": qc.FOCUS_BLOCK,
            "minimo_patches": qc.FOCUS_MIN_PATCHES,
        },
    })
