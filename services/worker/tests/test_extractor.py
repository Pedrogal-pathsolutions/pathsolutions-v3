import types
import unittest
from unittest import mock

import numpy as np
import torch

from pathsol_worker import extractor


class Dinov2ModelWithRegisters(torch.nn.Module):
    """Stand-in with the real class name: CLS, 4 registers and 256 patch tokens."""

    def __init__(self, tokens=261):
        super().__init__()
        self.tokens = tokens
        self.seen = None

    def forward(self, pixel_values):
        self.seen = pixel_values
        batch = pixel_values.shape[0]
        hidden = torch.arange(batch * self.tokens * 1024, dtype=torch.float32).reshape(batch, self.tokens, 1024)
        return types.SimpleNamespace(last_hidden_state=hidden, pooler_output=hidden[:, 0])


class OtherModel(Dinov2ModelWithRegisters):
    pass


def load_with(model):
    return mock.patch.object(extractor.AutoModel, "from_pretrained", return_value=model)


class Loading(unittest.TestCase):
    def test_refuses_a_model_without_registers(self):
        with load_with(OtherModel()), self.assertRaises(extractor.WrongModel):
            extractor.Extractor("/modelos/x", device="cpu", precision="fp32")

    def test_loads_offline_from_the_local_files(self):
        with load_with(Dinov2ModelWithRegisters()) as load:
            extractor.Extractor("/modelos/x", device="cpu", precision="fp32")
        _, kwargs = load.call_args
        self.assertEqual(load.call_args.args, ("/modelos/x",))
        self.assertTrue(kwargs["local_files_only"])
        self.assertTrue(kwargs["trust_remote_code"])
        self.assertEqual(kwargs["attn_implementation"], "eager")

    def test_unknown_precision(self):
        with load_with(Dinov2ModelWithRegisters()), self.assertRaises(ValueError):
            extractor.Extractor("/modelos/x", device="cpu", precision="bf16")


class Embedding(unittest.TestCase):
    def test_cls_in_float32_from_normalized_pixels(self):
        model = Dinov2ModelWithRegisters()
        with load_with(model):
            ex = extractor.Extractor("/modelos/x", device="cpu", precision="fp32")
        patches = np.zeros((2, 224, 224, 3), dtype=np.uint8)
        patches[1] = 255
        out = ex.embed(patches)
        self.assertEqual(out.shape, (2, 1024))
        self.assertEqual(out.dtype, np.float32)
        np.testing.assert_array_equal(out[1], np.arange(261 * 1024, 261 * 1024 + 1024, dtype=np.float32))
        seen = model.seen
        self.assertEqual(tuple(seen.shape), (2, 3, 224, 224))
        mean, std = np.array(extractor.MEAN), np.array(extractor.STD)
        np.testing.assert_allclose(seen[0, :, 0, 0].numpy(), -mean / std, rtol=1e-6)
        np.testing.assert_allclose(seen[1, :, 0, 0].numpy(), (1 - mean) / std, rtol=1e-6)

    def test_refuses_an_output_without_261_tokens(self):
        with load_with(Dinov2ModelWithRegisters(tokens=257)):
            ex = extractor.Extractor("/modelos/x", device="cpu", precision="fp32")
        with self.assertRaises(extractor.WrongModel):
            ex.embed(np.zeros((1, 224, 224, 3), dtype=np.uint8))

    def test_mean_and_std_of_the_plan(self):
        self.assertEqual(extractor.MEAN, (0.7068, 0.5755, 0.7220))
        self.assertEqual(extractor.STD, (0.1950, 0.2316, 0.1816))


if __name__ == "__main__":
    unittest.main()
