#!/usr/bin/python3
"""Copies the pinned Hibou-L revision to the modelos container (plan, section 10.1).

    enviar_modelo.py [--origem /data/modelos/hibou-L/<revision>]

Every file is checked first against the manifest of baixar_hibou.py; then each
goes in blocks, with VM1's identity, to modelos/hibou-L/<revision>/<file>,
committed with If-None-Match: * so that nothing already there is overwritten,
and checked by size and MD5. A file already there with the same MD5 counts as
sent; one with another MD5 stops everything.
"""
import argparse
import base64
import email.utils
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

CONTAINER = "https://pathsolwsiv3.blob.core.windows.net/modelos"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://storage.azure.com/"
)
X_MS_VERSION = "2024-11-04"
BLOCK = 8 * 1024 * 1024
SOURCE = "/data/modelos/hibou-L/31a3b9fee16554c8552cb643d311733bce8faf7c"


class Refused(Exception):
    pass


def _b64(raw):
    return base64.b64encode(raw).decode()


def digests(path):
    sha256, md5 = hashlib.sha256(), hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(BLOCK), b""):
            sha256.update(chunk)
            md5.update(chunk)
    return sha256.hexdigest(), md5.digest()


class Container:
    def __init__(self):
        with urlopen(Request(IMDS_TOKEN_URL, headers={"Metadata": "true"}), timeout=10) as response:
            self.token = json.load(response)["access_token"]

    def call(self, method, name, query=None, data=None, headers=None):
        url = f"{CONTAINER}/{urllib.parse.quote(name)}" + (f"?{urllib.parse.urlencode(query)}" if query else "")
        request = Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "x-ms-version": X_MS_VERSION,
            "x-ms-date": email.utils.formatdate(usegmt=True),
            **(headers or {}),
        })
        with urlopen(request, timeout=120) as response:
            return response.headers

    def stored(self, name):
        """(size, MD5 in base64) of the blob, or None."""
        try:
            headers = self.call("HEAD", name)
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            raise
        return int(headers["Content-Length"]), headers["Content-MD5"]

    def send(self, name, path, md5):
        ids = []
        with open(path, "rb") as f:
            for index, chunk in enumerate(iter(lambda: f.read(BLOCK), b"")):
                block = _b64(f"{index:08d}".encode())
                self.call("PUT", name, {"comp": "block", "blockid": block}, chunk, {"Content-MD5": _b64(hashlib.md5(chunk).digest())})
                ids.append(block)
        listing = "".join(f"<Latest>{escape(block)}</Latest>" for block in ids)
        self.call("PUT", name, {"comp": "blocklist"}, f"<?xml version='1.0' encoding='utf-8'?><BlockList>{listing}</BlockList>".encode(),
                  {"If-None-Match": "*", "x-ms-blob-content-md5": _b64(md5)})
        if self.stored(name) != (os.path.getsize(path), _b64(md5)):
            raise Refused(f"{name}: o blob gravado não confere em tamanho ou MD5")


def checked_files(source):
    with open(os.path.join(source, "manifesto.json")) as f:
        manifest = json.load(f)
    files = []
    for name, expected in sorted(manifest["files"].items()):
        path = os.path.join(source, name)
        sha256, md5 = digests(path)
        if (os.path.getsize(path), sha256) != (expected["size"], expected["sha256"]):
            raise Refused(f"{name} não confere com o manifesto")
        files.append((name, path, md5))
    path = os.path.join(source, "manifesto.json")
    files.append(("manifesto.json", path, digests(path)[1]))
    return manifest["revision"], files


def main(argv=None):
    parser = argparse.ArgumentParser(description="Copia a revisão fixada do Hibou-L para o container modelos.")
    parser.add_argument("--origem", default=SOURCE)
    args = parser.parse_args(argv)
    try:
        revision, files = checked_files(args.origem)
        container = Container()
        for name, path, md5 in files:
            blob = f"hibou-L/{revision}/{name}"
            there = container.stored(blob)
            if there is None:
                container.send(blob, path, md5)
                print(f"enviado: {blob}", flush=True)
            elif there == (os.path.getsize(path), _b64(md5)):
                print(f"já estava: {blob}", flush=True)
            else:
                raise Refused(f"{blob} já existe com outro conteúdo; nada foi sobrescrito")
    except (Refused, urllib.error.URLError, OSError, KeyError, ValueError) as error:
        print(f"FALHA: {error}", file=sys.stderr)
        return 1
    print(f"OK hibou-L/{revision}: {len(files)} arquivos no container modelos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
