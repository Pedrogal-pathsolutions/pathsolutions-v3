"""Azure Blob over REST, with VM2's managed identity (skill pathsol-contrato-h5, "Leitura da WSI" and "Escrita segura").

The worker reads WSIs (its role on the WSI containers only reads) and writes in
slide-h5 (its role there writes and never deletes). An upload goes in blocks,
each with its MD5, is committed with the MD5 of the whole file and is then
checked by size and MD5; a retry of the same job rewrites the same name.
"""
import base64
import email.utils
import hashlib
import os
import urllib.parse
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

from pathsol_worker import identidade

ACCOUNT = "https://pathsolwsiv3.blob.core.windows.net"
H5_CONTAINER = "slide-h5"
X_MS_VERSION = "2024-11-04"
BLOCK = 8 * 1024 * 1024


class BlobError(Exception):
    pass


def _b64(raw):
    return base64.b64encode(raw).decode()


class Blob:
    def __init__(self, opener=urlopen):
        self.opener = opener
        self.token = identidade.Token(identidade.STORAGE, opener)

    def _request(self, method, container, name, query=None, data=None, headers=None):
        url = f"{ACCOUNT}/{container}/{urllib.parse.quote(name)}"
        if query:
            url += f"?{urllib.parse.urlencode(query)}"
        request = Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {self.token()}",
            "x-ms-version": X_MS_VERSION,
            "x-ms-date": email.utils.formatdate(usegmt=True),
            **(headers or {}),
        })
        return self.opener(request, timeout=120)

    def download(self, container, name, path, sha256):
        """Streams the blob to path; a sha256 other than the job's leaves no file behind."""
        digest = hashlib.sha256()
        try:
            with self._request("GET", container, name) as response, open(path, "wb") as out:
                for chunk in iter(lambda: response.read(BLOCK), b""):
                    digest.update(chunk)
                    out.write(chunk)
            if digest.hexdigest() != sha256:
                raise BlobError(f"{container}/{name}: o sha256 não é o do job")
        except BaseException:
            if os.path.exists(path):
                os.remove(path)
            raise

    def upload(self, name, path, md5):
        ids = []
        with open(path, "rb") as f:
            for index, chunk in enumerate(iter(lambda: f.read(BLOCK), b"")):
                block = _b64(f"{index:08d}".encode())
                with self._request("PUT", H5_CONTAINER, name, {"comp": "block", "blockid": block}, chunk,
                                   {"Content-MD5": _b64(hashlib.md5(chunk).digest())}):
                    pass
                ids.append(block)
        listing = "".join(f"<Latest>{escape(block)}</Latest>" for block in ids)
        with self._request("PUT", H5_CONTAINER, name, {"comp": "blocklist"},
                           f"<?xml version='1.0' encoding='utf-8'?><BlockList>{listing}</BlockList>".encode(),
                           {"x-ms-blob-content-md5": _b64(md5), "x-ms-blob-content-type": "application/x-hdf5"}):
            pass
        with self._request("HEAD", H5_CONTAINER, name) as response:
            size, stored = int(response.headers["Content-Length"]), response.headers["Content-MD5"]
        if size != os.path.getsize(path) or stored != _b64(md5):
            raise BlobError(f"{H5_CONTAINER}/{name}: o blob gravado não confere em tamanho ou MD5")
