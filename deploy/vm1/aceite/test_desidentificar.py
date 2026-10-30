"""De-identification of synthetic Aperio SVS files with label and macro.

Runs in the worker test image, which has tifffile and OpenSlide:

    docker run --rm --network none -v "$PWD/deploy/vm1/aceite:/aceite:ro" -e PYTHONPATH=/aceite \
        pathsol-worker-teste:<tag> unittest discover -s /aceite -p 'test_desidentificar.py'
"""
import hashlib
import os
import tempfile
import unittest

import desidentificar

try:
    import numpy as np
    import openslide
    import tifffile
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste do worker") from None

SECRETS = (b"caso-12345", b"fulano", b"98765", b"SS1234", b"10/30/26")
HEADER = "Aperio Image Library v12.0.15\r\n2048x1024 [0,0 2048x1024] (256x256) RGB"
DESCRIPTION = (f"{HEADER}|AppMag = 40|Filename = caso-12345|User = fulano|ScanScope ID = SS1234"
               "|Date = 10/30/26|Barcode = 98765|MPP = 0.25")


def write_aperio(path, bigtiff=False):
    rng = np.random.default_rng(0)
    level0 = rng.integers(0, 256, (1024, 2048, 3), dtype=np.uint8)
    with tifffile.TiffWriter(path, bigtiff=bigtiff) as tif:
        tif.write(level0, tile=(256, 256), photometric="rgb", compression="zlib", description=DESCRIPTION,
                  metadata=None, datetime="2026:10:30 10:00:00", software="Scanner 1.0")
        tif.write(level0[::8, ::8], photometric="rgb", description=f"{HEADER} -> 256x128|AppMag = 40|Filename = caso-12345",
                  metadata=None)
        tif.write(np.ascontiguousarray(level0[::4, ::4]), tile=(256, 256), photometric="rgb", compression="zlib",
                  description="Aperio Image Library v12.0.15\r\n512x256", metadata=None)
        tif.write(np.full((100, 100, 3), 77, dtype=np.uint8), photometric="rgb", subfiletype=1,
                  description="Aperio Image Library v12.0.15\r\nlabel 100x100", metadata=None)
        tif.write(np.full((100, 200, 3), 88, dtype=np.uint8), photometric="rgb", subfiletype=9,
                  description="Aperio Image Library v12.0.15\r\nmacro 200x100", metadata=None)
    return level0


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


class Deidentify(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.dir.cleanup)

    def check(self, bigtiff):
        source = os.path.join(self.dir.name, "origem.svs")
        target = os.path.join(self.dir.name, "copia.svs")
        level0 = write_aperio(source, bigtiff)
        before = sha256(source)
        with openslide.OpenSlide(source) as slide:
            self.assertEqual(set(slide.associated_images), {"thumbnail", "label", "macro"})  # the test file is realistic
        removed = desidentificar.deidentify(source, target)
        self.assertEqual(removed, 2)
        self.assertEqual(sha256(source), before)
        with open(target, "rb") as f:
            raw = f.read()
        for secret in SECRETS:
            self.assertNotIn(secret, raw)
        self.assertNotIn(bytes([77]) * 3000, raw)
        self.assertNotIn(bytes([88]) * 3000, raw)
        with openslide.OpenSlide(target) as slide:
            self.assertEqual(set(slide.associated_images), {"thumbnail"})
            self.assertEqual(slide.level_count, 2)
            self.assertEqual(slide.properties[openslide.PROPERTY_NAME_MPP_X], "0.25")
            self.assertEqual(slide.properties["aperio.AppMag"], "40")
            for key in slide.properties:
                self.assertNotRegex(key, r"aperio\.(Filename|User|ScanScope ID|Date|Barcode)$")
            region = np.asarray(slide.read_region((256, 256), 0, (256, 256)).convert("RGB"))
        np.testing.assert_array_equal(region, level0[256:512, 256:512])
        with tifffile.TiffFile(source) as a, tifffile.TiffFile(target) as b:
            self.assertEqual(a.pages[0].dataoffsets, b.pages[0].dataoffsets)

    def test_classic_tiff(self):
        self.check(bigtiff=False)

    def test_bigtiff(self):
        self.check(bigtiff=True)

    def test_refuses_a_file_that_is_not_aperio(self):
        source = os.path.join(self.dir.name, "outro.tif")
        tifffile.imwrite(source, np.zeros((64, 64, 3), dtype=np.uint8), description="generic", metadata=None)
        with self.assertRaises(desidentificar.NotAperio):
            desidentificar.deidentify(source, os.path.join(self.dir.name, "copia.svs"))
        self.assertFalse(os.path.exists(os.path.join(self.dir.name, "copia.svs")))

    def test_never_overwrites_the_target(self):
        source = os.path.join(self.dir.name, "origem.svs")
        write_aperio(source)
        target = os.path.join(self.dir.name, "copia.svs")
        with open(target, "wb") as f:
            f.write(b"ja existe")
        with self.assertRaises(FileExistsError):
            desidentificar.deidentify(source, target)


class Description(unittest.TestCase):
    def test_keeps_the_header_and_the_allowed_fields(self):
        self.assertEqual(desidentificar.clean_description(DESCRIPTION), f"{HEADER}|AppMag = 40|MPP = 0.25")


if __name__ == "__main__":
    unittest.main()
