"""De-identification of a real Aperio SVS (plan, section 17: CMU-1.svs, CC0-1.0, from the OpenSlide test data).

Skipped unless PATHSOL_SVS_REAL names the file. Runs in the worker test image, with
the original read-only and the copy in TMPDIR, deleted at the end:

    docker run --rm --network none --user "$(id -u):$(id -g)" -v /data/staging/aceite:/origem:ro \
        -v "$TRABALHO:/trabalho" -e TMPDIR=/trabalho -e PATHSOL_SVS_REAL=/origem/CMU-1.svs \
        -v "$PWD/deploy/vm1/aceite:/aceite:ro" -e PYTHONPATH=/aceite \
        pathsol-worker-teste:<tag> unittest discover -s /aceite -p 'test_desidentificar_real.py'
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

SOURCE = os.environ.get("PATHSOL_SVS_REAL")
IDENTIFYING = ("Filename", "User", "ScanScope ID", "Date", "Time")
CHANGED_TAGS = (desidentificar.DESCRIPTION, *desidentificar.TEXT_TAGS)


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def segments(path, page):
    """sha256 of a directory's compressed tiles or strips, in order."""
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for offset, count in zip(page.dataoffsets, page.databytecounts):
            f.seek(offset)
            digest.update(f.read(count))
    return digest.hexdigest()


@unittest.skipUnless(SOURCE, "PATHSOL_SVS_REAL não definido")
class RealSlide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        work = tempfile.TemporaryDirectory()
        cls.addClassCleanup(work.cleanup)
        cls.target = os.path.join(work.name, "copia.svs")
        cls.before = sha256(SOURCE)
        cls.removed = desidentificar.deidentify(SOURCE, cls.target)
        cls.source = openslide.OpenSlide(SOURCE)
        cls.addClassCleanup(cls.source.close)
        cls.copy = openslide.OpenSlide(cls.target)
        cls.addClassCleanup(cls.copy.close)

    def test_the_original_does_not_change(self):
        self.assertEqual(sha256(SOURCE), self.before)

    def test_label_and_macro_leave_and_their_bytes_are_zeroed(self):
        self.assertEqual(set(self.source.associated_images), {"thumbnail", "label", "macro"})
        self.assertEqual(set(self.copy.associated_images), {"thumbnail"})
        self.assertEqual(self.removed, 2)
        with tifffile.TiffFile(SOURCE) as tif, open(self.target, "rb") as f:
            dropped = [page for i, page in enumerate(tif.pages) if not page.is_tiled and i != 1]
            self.assertEqual(len(dropped), 2)
            for page in dropped:
                for offset, count in zip(page.dataoffsets, page.databytecounts):
                    f.seek(offset)
                    self.assertEqual(f.read(count), bytes(count))

    def test_identifying_fields_leave_the_properties_and_the_bytes(self):
        values = [self.source.properties[f"aperio.{field}"] for field in IDENTIFYING]
        self.assertTrue(all(values))
        for field in IDENTIFYING:
            self.assertNotIn(f"aperio.{field}", self.copy.properties)
        self.assertEqual(self.copy.properties["tiff.ImageDescription"],
                         desidentificar.clean_description(self.source.properties["tiff.ImageDescription"]))
        with open(self.target, "rb") as f:
            raw = f.read()
        for value in values:
            self.assertNotIn(value.encode("latin-1"), raw)

    def test_levels_scale_and_pixels_stay(self):
        for name in ("level_count", "level_dimensions", "level_downsamples"):
            self.assertEqual(getattr(self.copy, name), getattr(self.source, name))
        for key in (openslide.PROPERTY_NAME_MPP_X, openslide.PROPERTY_NAME_MPP_Y, "aperio.AppMag"):
            self.assertEqual(self.copy.properties[key], self.source.properties[key])
        for level, (width, height) in enumerate(self.source.level_dimensions):
            downsample = self.source.level_downsamples[level]
            at = (int(width // 2 * downsample), int(height // 2 * downsample))
            np.testing.assert_array_equal(np.asarray(self.copy.read_region(at, level, (512, 512))),
                                          np.asarray(self.source.read_region(at, level, (512, 512))))
        np.testing.assert_array_equal(np.asarray(self.copy.associated_images["thumbnail"]),
                                      np.asarray(self.source.associated_images["thumbnail"]))

    def test_kept_directories_keep_their_tiles_and_tags(self):
        with tifffile.TiffFile(SOURCE) as a, tifffile.TiffFile(self.target) as b:
            kept = [page for i, page in enumerate(a.pages) if page.is_tiled or i == 1]
            self.assertEqual(len(kept), len(b.pages))
            for old, new in zip(kept, b.pages):
                self.assertEqual((old.offset, old.dataoffsets, old.databytecounts),
                                 (new.offset, new.dataoffsets, new.databytecounts))
                self.assertEqual(segments(SOURCE, old), segments(self.target, new))
                tags = {tag.code for tag in old.tags.values()} - set(CHANGED_TAGS)
                self.assertEqual(tags, {tag.code for tag in new.tags.values()} - set(CHANGED_TAGS))
                for code in tags:
                    np.testing.assert_array_equal(np.asarray(new.tags[code].value), np.asarray(old.tags[code].value))


if __name__ == "__main__":
    unittest.main()
