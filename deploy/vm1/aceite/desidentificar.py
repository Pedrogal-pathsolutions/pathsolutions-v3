#!/usr/bin/python3
"""De-identification of an Aperio SVS before it leaves the operator (plan, sections 12.3 and 17; decision 6).

Works on a copy, never on the original. The label, the macro and any other
image outside the pyramid leave the TIFF chain and have their bytes zeroed;
the thumbnail (the second directory, tissue only) stays. Every
ImageDescription keeps its header and only the fields in KEEP_FIELDS, and the
other text tags are blanked. The pyramid's tiles stay byte for byte.

    desidentificar.py ORIGEM DESTINO
"""
import dataclasses
import struct
import sys

DESCRIPTION, STRIP_OFFSETS, STRIP_COUNTS, TILE_OFFSETS, TILE_COUNTS = 270, 273, 279, 324, 325
# Document name, page name, software, date and time, artist, host computer, copyright.
TEXT_TAGS = (269, 285, 305, 306, 315, 316, 33432)
KEEP_FIELDS = ("AppMag", "MPP")
TYPE_SIZES = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 6: 1, 7: 1, 8: 2, 9: 4, 10: 8, 11: 4, 12: 8, 16: 8, 17: 8, 18: 8}
VALUE_FORMATS = {3: "H", 4: "I", 16: "Q"}


class NotAperio(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Entry:
    type: int
    count: int
    value_at: int
    size: int


@dataclasses.dataclass(frozen=True)
class Ifd:
    offset: int
    entries: dict
    end: int
    next_at: int


class Tiff:
    def __init__(self, f):
        self.f = f
        head = f.read(16)
        self.order = {b"II": "<", b"MM": ">"}.get(head[:2])
        if self.order is None:
            raise NotAperio("não é TIFF")
        magic = struct.unpack(self.order + "H", head[2:4])[0]
        if magic not in (42, 43):
            raise NotAperio("não é TIFF")
        self.big = magic == 43
        self.pointer = "Q" if self.big else "I"
        self.pointer_size = 8 if self.big else 4
        self.first_at = 8 if self.big else 4
        self.ifds = self._chain(struct.unpack(self.order + self.pointer, head[self.first_at:self.first_at + self.pointer_size])[0])

    def _read(self, at, size):
        self.f.seek(at)
        return self.f.read(size)

    def _chain(self, offset):
        ifds, seen = [], set()
        count_size, entry_size = (8, 20) if self.big else (2, 12)
        while offset:
            if offset in seen:
                raise NotAperio("diretórios do TIFF em ciclo")
            seen.add(offset)
            n = struct.unpack(self.order + ("Q" if self.big else "H"), self._read(offset, count_size))[0]
            base = offset + count_size
            raw = self._read(base, n * entry_size)
            entries = {}
            for i in range(n):
                field = raw[i * entry_size:(i + 1) * entry_size]
                tag, kind = struct.unpack(self.order + "HH", field[:4])
                count = struct.unpack(self.order + self.pointer, field[4:4 + self.pointer_size])[0]
                size = TYPE_SIZES.get(kind, 1) * count
                value_field = base + i * entry_size + 4 + self.pointer_size
                at = value_field
                if size > self.pointer_size:
                    at = struct.unpack(self.order + self.pointer, field[4 + self.pointer_size:])[0]
                entries[tag] = Entry(kind, count, at, size)
            next_at = base + n * entry_size
            ifds.append(Ifd(offset, entries, next_at + self.pointer_size, next_at))
            offset = struct.unpack(self.order + self.pointer, self._read(next_at, self.pointer_size))[0]
        return ifds

    def values(self, entry):
        return struct.unpack(self.order + VALUE_FORMATS[entry.type] * entry.count, self._read(entry.value_at, entry.size))

    def text(self, entry):
        return self._read(entry.value_at, entry.size).split(b"\0", 1)[0].decode("latin-1")


def clean_description(text):
    header, *fields = text.split("|")
    return "|".join([header, *(f for f in fields if f.split("=", 1)[0].strip() in KEEP_FIELDS)])


def deidentify(source, target):
    """Writes the de-identified copy; returns how many images outside the pyramid were removed."""
    with open(source, "rb") as original:
        tiff = Tiff(original)
        first = tiff.ifds[0].entries.get(DESCRIPTION)
        if first is None or not tiff.text(first).startswith("Aperio"):
            raise NotAperio("o primeiro diretório não é de um SVS da Aperio")
        keep = [ifd for i, ifd in enumerate(tiff.ifds) if TILE_OFFSETS in ifd.entries or i == 1]
        drop = [ifd for ifd in tiff.ifds if ifd not in keep]
        zeros, writes = [], []
        for ifd in drop:
            offsets, counts = (STRIP_OFFSETS, STRIP_COUNTS) if STRIP_OFFSETS in ifd.entries else (TILE_OFFSETS, TILE_COUNTS)
            zeros += zip(tiff.values(ifd.entries[offsets]), tiff.values(ifd.entries[counts]))
            zeros += [(e.value_at, e.size) for e in ifd.entries.values() if e.size > tiff.pointer_size]
            zeros.append((ifd.offset, ifd.end - ifd.offset))
        for ifd, following in zip(keep, keep[1:] + [None]):
            writes.append((ifd.next_at, struct.pack(tiff.order + tiff.pointer, following.offset if following else 0)))
            for tag, entry in ifd.entries.items():
                if tag == DESCRIPTION:
                    cleaned = clean_description(tiff.text(entry)).encode("latin-1")
                    writes.append((entry.value_at, cleaned + b"\0" * (entry.size - len(cleaned))))
                elif tag in TEXT_TAGS:
                    zeros.append((entry.value_at, entry.size))
        with open(target, "xb") as copy:
            original.seek(0)
            for chunk in iter(lambda: original.read(8 << 20), b""):
                copy.write(chunk)
    with open(target, "r+b") as f:
        for at, size in zeros:
            f.seek(at)
            f.write(b"\0" * size)
        for at, data in writes:
            f.seek(at)
            f.write(data)
    _verify(target, len(keep))
    return len(drop)


def _verify(target, expected):
    with open(target, "rb") as f:
        tiff = Tiff(f)
        if len(tiff.ifds) != expected:
            raise NotAperio("a cópia ficou com diretórios de imagem fora da pirâmide")
        for i, ifd in enumerate(tiff.ifds):
            if TILE_OFFSETS not in ifd.entries and i != 1:
                raise NotAperio("a cópia ficou com uma imagem fora da pirâmide")
            entry = ifd.entries.get(DESCRIPTION)
            if entry is not None and clean_description(tiff.text(entry)) != tiff.text(entry):
                raise NotAperio("a cópia ficou com campos de fora da lista de permissão")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("uso: desidentificar.py ORIGEM DESTINO")
    print(f"OK: {deidentify(sys.argv[1], sys.argv[2])} imagens fora da pirâmide removidas")
