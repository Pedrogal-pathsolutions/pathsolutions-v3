"""Hibou-L, frozen, loaded offline from the pinned local files (plan, sections 10.1 and 10.2)."""
import numpy as np
import torch
from transformers import AutoModel

# Plan 10.2.
MEAN = (0.7068, 0.5755, 0.7220)
STD = (0.1950, 0.2316, 0.1816)
MODEL_CLASS = "Dinov2ModelWithRegisters"
# The pinned code has only eager attention (modeling_dinov2.py, Dinov2SelfAttention).
ATTENTION = "eager"
# CLS, 4 registers and 16 x 16 patch tokens of 14 px.
TOKENS = 261
PRECISIONS = ("fp16", "fp32")


class WrongModel(Exception):
    pass


class Extractor:
    def __init__(self, model_dir, device, precision):
        if precision not in PRECISIONS:
            raise ValueError(f"precisão desconhecida: {precision}")
        # Without trust_remote_code, transformers 4.57 falls back to a class
        # without registers and only says so at INFO level.
        model = AutoModel.from_pretrained(
            model_dir, local_files_only=True, trust_remote_code=True, attn_implementation=ATTENTION
        )
        if type(model).__name__ != MODEL_CLASS:
            raise WrongModel(f"classe {type(model).__name__}, e não {MODEL_CLASS}")
        self.device = torch.device(device)
        self.model = model.to(self.device).eval()
        self.fp16 = precision == "fp16"
        self.mean = torch.tensor(MEAN, device=self.device).view(1, 3, 1, 1)
        self.std = torch.tensor(STD, device=self.device).view(1, 3, 1, 1)

    @torch.inference_mode()
    def embed(self, patches):
        """(B, 224, 224, 3) uint8 patches to (B, 1024) float32 CLS embeddings."""
        x = torch.from_numpy(np.require(patches, np.uint8, ("C", "W"))).to(self.device)
        x = (x.permute(0, 3, 1, 2).float().div_(255) - self.mean) / self.std
        with torch.autocast(device_type=self.device.type, dtype=torch.float16, enabled=self.fp16):
            out = self.model(pixel_values=x)
        if out.last_hidden_state.shape[1] != TOKENS:
            raise WrongModel(f"{out.last_hidden_state.shape[1]} tokens, e não {TOKENS}")
        return out.pooler_output.float().cpu().numpy()
