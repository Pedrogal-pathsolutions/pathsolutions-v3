#!/usr/bin/python3
"""Operator script of the acceptance slides (plan, section 17; decision 6; Phase 4, slice 10).

    pathsol_enviar_lamina.py --tenant SLUG --arquivo /data/staging/aceite/<file> \
        --material M --coloracao C [--orgao O]

The file must be in the staging directory, which has a cap. The slide gets a
UUID at once, and the original name is never printed. A de-identified copy is
made (desidentificar.py), and its sha256 is the one registered. It goes to the
tenant's WSI container with a user delegation SAS signed by VM1, for that blob
alone, create-only and short, in blocks with their MD5, committed with
If-None-Match: *; VM1's identity then checks size and MD5. The slide is
registered with the test producer, and only then the staging files are
deleted. Nothing in the storage is ever deleted.
"""
import argparse
import base64
import dataclasses
import datetime
import email.utils
import hashlib
import hmac
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import uuid
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from xml.sax.saxutils import escape

import desidentificar

ACCOUNT = "pathsolwsiv3"
BLOB = f"https://{ACCOUNT}.blob.core.windows.net"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://storage.azure.com/"
)
STAGING = "/data/staging/aceite"
STAGING_CAP = 20 * 1024**3
# Phase 3, slice 8: a create-only SAS with blocks needs requests at 2026-04-06
# or later; the SAS itself is signed as 2026-02-06.
REQUEST_VERSION = "2026-04-06"
SAS_VERSION = "2026-02-06"
SAS_MINUTES = 60
BLOCK = 8 * 1024 * 1024
PRODUCER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "produtor", "pathsol_produtor.py")


class Refused(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class DelegationKey:
    oid: str
    tid: str
    start: str
    expiry: str
    service: str
    version: str
    value: str


def _b64(raw):
    return base64.b64encode(raw).decode()


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def token():
    with urlopen(Request(IMDS_TOKEN_URL, headers={"Metadata": "true"}), timeout=10) as response:
        return json.load(response)["access_token"]


def _call(url, method="PUT", data=None, headers=None):
    request = Request(url, data=data, method=method, headers={
        "x-ms-version": REQUEST_VERSION,
        "x-ms-date": email.utils.formatdate(usegmt=True),
        **(headers or {}),
    })
    with urlopen(request, timeout=120) as response:
        return response.read(), response.headers


def delegation_key(bearer, start, expiry):
    body = f"<?xml version='1.0' encoding='utf-8'?><KeyInfo><Start>{start}</Start><Expiry>{expiry}</Expiry></KeyInfo>"
    raw, _ = _call(f"{BLOB}/?restype=service&comp=userdelegationkey", "POST", body.encode(),
                   {"Authorization": f"Bearer {bearer}", "Content-Type": "application/xml"})
    root = ElementTree.fromstring(raw)
    return DelegationKey(*(root.findtext(field) for field in
                           ("SignedOid", "SignedTid", "SignedStart", "SignedExpiry", "SignedService", "SignedVersion", "Value")))


def string_to_sign(permissions, start, expiry, resource, key):
    """Version 2025-07-05 and later (Create a user delegation SAS), https only, every optional field empty."""
    return "\n".join([
        permissions, start, expiry, resource,
        key.oid, key.tid, key.start, key.expiry, key.service, key.version,
        "", "", "", "", "",  # saoid, suoid, scid, skdutid, sduoid
        "", "https", SAS_VERSION, "b", "", "",  # sip, spr, sv, sr, snapshot, encryption scope
        "", "", "", "", "",  # rscc, rscd, rsce, rscl, rsct
    ])


def sas(container, name, key, start, expiry):
    """Query string of a create-only SAS for this blob alone."""
    text = string_to_sign("c", start, expiry, f"/blob/{ACCOUNT}/{container}/{name}", key)
    signature = _b64(hmac.new(base64.b64decode(key.value), text.encode(), "sha256").digest())
    return urllib.parse.urlencode({
        "sv": SAS_VERSION, "sr": "b", "sp": "c", "st": start, "se": expiry, "spr": "https",
        "skoid": key.oid, "sktid": key.tid, "skt": key.start, "ske": key.expiry, "sks": key.service, "skv": key.version,
        "sig": signature,
    })


def upload(container, name, path, md5, query):
    base = f"{BLOB}/{container}/{urllib.parse.quote(name)}"
    ids = []
    with open(path, "rb") as f:
        for index, chunk in enumerate(iter(lambda: f.read(BLOCK), b"")):
            block = _b64(f"{index:08d}".encode())
            _call(f"{base}?comp=block&blockid={urllib.parse.quote(block)}&{query}", data=chunk,
                  headers={"Content-MD5": _b64(hashlib.md5(chunk).digest())})
            ids.append(block)
    listing = "".join(f"<Latest>{escape(block)}</Latest>" for block in ids)
    _call(f"{base}?comp=blocklist&{query}", data=f"<?xml version='1.0' encoding='utf-8'?><BlockList>{listing}</BlockList>".encode(),
          headers={"If-None-Match": "*", "x-ms-blob-content-md5": _b64(md5)})


def check(container, name, path, md5, bearer):
    _, headers = _call(f"{BLOB}/{container}/{urllib.parse.quote(name)}", "HEAD", headers={"Authorization": f"Bearer {bearer}"})
    if (int(headers["Content-Length"]), headers["Content-MD5"]) != (os.path.getsize(path), _b64(md5)):
        raise Refused(f"{container}/{name}: o blob gravado não confere em tamanho ou MD5")


def staged(path):
    real = os.path.realpath(path)
    if os.path.dirname(real) != os.path.realpath(STAGING) or not os.path.isfile(real):
        raise Refused(f"o arquivo precisa estar em {STAGING}")
    total = sum(os.path.getsize(os.path.join(STAGING, name)) for name in os.listdir(STAGING))
    if total > STAGING_CAP:
        raise Refused(f"o staging tem {total} bytes, acima do teto de {STAGING_CAP}")
    return real


def digests(path):
    sha256, md5 = hashlib.sha256(), hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(BLOCK), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.digest()


def describe(error):
    """Never the original name: file errors carry the path."""
    if isinstance(error, OSError) and not isinstance(error, urllib.error.URLError):
        return error.strerror or type(error).__name__
    if isinstance(error, subprocess.CalledProcessError):
        return error.stderr.strip()
    return str(error)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Envia uma lâmina de aceite desidentificada ao container do tenant.")
    parser.add_argument("--tenant", required=True, choices=("publico",))
    parser.add_argument("--arquivo", required=True)
    parser.add_argument("--material", required=True, choices=("biopsia", "peca", "citologia"))
    parser.add_argument("--coloracao", required=True)
    parser.add_argument("--orgao", default="")
    args = parser.parse_args(argv)
    container = f"wsi-{args.tenant}"
    try:
        original = staged(args.arquivo)
        extension = os.path.splitext(original)[1].lower().lstrip(".")
        if not re.fullmatch(r"[a-z0-9]{2,5}", extension):
            raise Refused("extensão inválida")
        slide = str(uuid.uuid4())
        name = f"{slide}.{extension}"
        copy = os.path.join(STAGING, name)
        removed = desidentificar.deidentify(original, copy)
        sha256, md5 = digests(copy)
        bearer = token()
        now = datetime.datetime.now(datetime.UTC).replace(microsecond=0)
        start = (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")
        expiry = (now + datetime.timedelta(minutes=SAS_MINUTES)).strftime("%Y-%m-%dT%H:%M:%SZ")
        key = delegation_key(bearer, start, expiry)
        upload(container, name, copy, md5, sas(container, name, key, start, expiry))
        check(container, name, copy, md5, bearer)
        run(["python3", PRODUCER, "lamina", "--tenant", args.tenant, "--arquivo", name, "--sha256", sha256,
             "--material", args.material, "--coloracao", args.coloracao, *(["--orgao", args.orgao] if args.orgao else [])])
        os.remove(copy)
        os.remove(original)
    except (Refused, desidentificar.NotAperio, urllib.error.URLError, OSError, subprocess.CalledProcessError) as error:
        print(f"FALHA: {describe(error)}", file=sys.stderr)
        return 1
    print(f"OK lâmina {slide} em {container}: sha256 {sha256}; {removed} imagens fora da pirâmide removidas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
