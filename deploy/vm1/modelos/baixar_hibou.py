#!/usr/bin/python3
"""Downloads the pinned Hibou-L revision from Hugging Face (plan, section 10.1).

Run by the operator in their own terminal on VM1:

    python3 deploy/vm1/modelos/baixar_hibou.py

The token is read with getpass, goes only to huggingface.co (never to the CDN
the file URLs redirect to) and is never written to disk or printed. Each file
is checked against the revision's listing (sha256 for LFS files, git's blob
hash for the others), and the weights also against the sha256 fixed in the
plan, before it takes its final name. The result is
/data/modelos/hibou-L/<revision>/, with a manifesto.json of sizes and sha256.
"""
import argparse
import getpass
import hashlib
import json
import os
import shutil
import sys
import urllib.error
import urllib.request

REPO = "histai/hibou-L"
REVISION = "31a3b9fee16554c8552cb643d311733bce8faf7c"
PINS = {"model.safetensors": "a63d1699448143ceccf2b7e1c4bf35b995c51f86ef8a6efb471af2eee210b79c"}
API_URL = f"https://huggingface.co/api/models/{REPO}/revision/{REVISION}?blobs=true"
FILE_URL = f"https://huggingface.co/{REPO}/resolve/{REVISION}/{{path}}"
DEST = "/data/modelos/hibou-L"
# The revision has ~1.2 GB; a bigger listing is not the revision of the plan.
MAX_TOTAL_BYTES = 2 * 1024**3
FREE_MARGIN = 1024**3
CHUNK = 8 * 1024 * 1024
PARTIAL = ".parcial."


class Refused(Exception):
    pass


def git_blob_sha1(content):
    return hashlib.sha1(b"blob %d\0" % len(content) + content).hexdigest()


def authorized(url, token):
    request = urllib.request.Request(url)
    # The file URLs redirect to a CDN, which must not receive the token.
    request.add_unredirected_header("Authorization", f"Bearer {token}")
    return request


def plain_name(name):
    return name not in ("", ".", "..") and os.path.basename(name) == name and "\\" not in name


def expected_files(info, pins):
    if info.get("sha") != REVISION:
        raise Refused(f"a API devolveu a revisão {info.get('sha')!r}, e não a do plano")
    files = {}
    for entry in info.get("siblings", []):
        name = entry["rfilename"]
        if not plain_name(name):
            raise Refused(f"nome de arquivo fora do diretório: {name!r}")
        lfs = entry.get("lfs")
        files[name] = {
            "size": entry["size"],
            "sha256": lfs["sha256"] if lfs else None,
            "git_sha1": None if lfs else entry["blobId"],
        }
    for name, sha256 in pins.items():
        if files.get(name, {}).get("sha256") != sha256:
            raise Refused(f"{name}: o sha256 da revisão não é o fixado no plano")
    total = sum(f["size"] for f in files.values())
    if total > MAX_TOTAL_BYTES:
        raise Refused(f"a revisão tem {total} bytes, acima do teto de {MAX_TOTAL_BYTES}")
    return files


def digest(chunks, expected, sink=None):
    """Hashes a stream the way the listing does; returns (matches, sha256)."""
    sha256 = hashlib.sha256()
    git = hashlib.sha1(b"blob %d\0" % expected["size"])
    size = 0
    for chunk in chunks:
        size += len(chunk)
        sha256.update(chunk)
        git.update(chunk)
        if sink is not None:
            sink.write(chunk)
    if expected["sha256"]:
        same = sha256.hexdigest() == expected["sha256"]
    else:
        same = git.hexdigest() == expected["git_sha1"]
    return size == expected["size"] and same, sha256.hexdigest()


def fetch(opener, token, name, expected, directory):
    """Downloads one file under a partial name; returns (sha256, downloaded)."""
    final = os.path.join(directory, name)
    if os.path.exists(final):
        with open(final, "rb") as f:
            same, sha256 = digest(iter(lambda: f.read(CHUNK), b""), expected)
        if not same:
            raise Refused(f"{name} já existe e não confere com a revisão; nada foi sobrescrito")
        return sha256, False
    partial = os.path.join(directory, PARTIAL + name)
    try:
        with opener(authorized(FILE_URL.format(path=name), token)) as response, open(partial, "wb") as out:
            same, sha256 = digest(iter(lambda: response.read(CHUNK), b""), expected, sink=out)
            out.flush()
            os.fsync(out.fileno())
        if not same:
            raise Refused(f"{name}: tamanho ou hash diferente do da revisão")
        os.replace(partial, final)
    finally:
        if os.path.exists(partial):
            os.remove(partial)
    return sha256, True


def download_revision(opener, token, dest, pins=None):
    with opener(authorized(API_URL, token)) as response:
        info = json.load(response)
    files = expected_files(info, PINS if pins is None else pins)
    directory = os.path.join(dest, REVISION)
    os.makedirs(directory, mode=0o755, exist_ok=True)
    missing = sum(f["size"] for name, f in files.items() if not os.path.exists(os.path.join(directory, name)))
    if shutil.disk_usage(directory).free < missing + FREE_MARGIN:
        raise Refused(f"espaço livre insuficiente em {directory}")
    manifest = {
        "repo": REPO,
        "revision": REVISION,
        "license": (info.get("cardData") or {}).get("license"),
        "files": {},
    }
    for name, expected in sorted(files.items()):
        sha256, downloaded = fetch(opener, token, name, expected, directory)
        manifest["files"][name] = {"size": expected["size"], "sha256": sha256}
        print(f"{'baixado' if downloaded else 'já estava'}: {name} ({expected['size']} bytes)", flush=True)
    path = os.path.join(directory, "manifesto.json")
    partial = os.path.join(directory, PARTIAL + "manifesto.json")
    with open(partial, "w") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(partial, path)
    return manifest


def describe(error):
    if isinstance(error, urllib.error.HTTPError) and error.code in (401, 403):
        return f"o Hugging Face recusou o token (HTTP {error.code}); o acesso ao {REPO} está liberado nessa conta?"
    return str(error)


def main(argv=None, opener=None):
    parser = argparse.ArgumentParser(description=f"Baixa {REPO} na revisão {REVISION}.")
    parser.add_argument("--destino", default=DEST)
    args = parser.parse_args(argv)
    if opener is None:
        opener = lambda request: urllib.request.urlopen(request, timeout=60)  # noqa: E731
    token = getpass.getpass("Token do Hugging Face (não aparece na tela): ").strip()
    if not token:
        print("FALHA: token vazio", file=sys.stderr)
        return 1
    try:
        manifest = download_revision(opener, token, args.destino)
    except (Refused, urllib.error.URLError, OSError, ValueError, KeyError) as error:
        print(f"FALHA: {describe(error).replace(token, '<token>')}", file=sys.stderr)
        return 1
    directory = os.path.join(args.destino, REVISION)
    print(f"OK {REPO}@{REVISION}: {len(manifest['files'])} arquivos em {directory}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
