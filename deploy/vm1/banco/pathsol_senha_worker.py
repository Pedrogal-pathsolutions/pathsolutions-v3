#!/usr/bin/python3
"""Sets the worker's database password (Pedro's option A of 30/10: Key Vault).

    pathsol_senha_worker.py

A new password goes first to the secret banco-worker of pathsol-kv-v3, with
VM1's identity (Key Vault Secrets Officer on the vault), and only then to the
role pathsol_worker, which gets LOGIN. The role receives a SCRAM verifier
computed here and sent by stdin, so the password never reaches PostgreSQL, a
log or a command line, and it is never printed. The worker on VM2 reads the
secret with its own identity, which may read that secret alone. Running it
again rotates the password.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import subprocess
import sys
import urllib.error
from urllib.request import Request, urlopen

DATABASE = "pathsol-banco"
SECRET_URL = "https://pathsol-kv-v3.vault.azure.net/secrets/banco-worker?api-version=7.4"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https%3A%2F%2Fvault.azure.net"
)
ITERATIONS = 4096


def scram_verifier(password, salt, iterations):
    """The SCRAM-SHA-256 verifier PostgreSQL stores for this password and salt."""
    salted = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    client = hmac.new(salted, b"Client Key", "sha256").digest()
    server = hmac.new(salted, b"Server Key", "sha256").digest()
    encode = lambda raw: base64.b64encode(raw).decode()  # noqa: E731
    return f"SCRAM-SHA-256${iterations}:{encode(salt)}${encode(hashlib.sha256(client).digest())}:{encode(server)}"


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def token():
    with urlopen(Request(IMDS_TOKEN_URL, headers={"Metadata": "true"}), timeout=10) as response:
        return json.load(response)["access_token"]


def store(password):
    body = json.dumps({"value": password, "contentType": "senha do pathsol_worker"}).encode()
    request = Request(SECRET_URL, data=body, method="PUT",
                      headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"})
    with urlopen(request, timeout=30):
        pass


def main(argv=None):
    password = secrets.token_urlsafe(32)
    try:
        store(password)
    except (urllib.error.URLError, OSError) as error:
        print(f"FALHA no cofre: {error}; o papel não mudou", file=sys.stderr)
        return 1
    verifier = scram_verifier(password, os.urandom(16), ITERATIONS)
    try:
        run(["docker", "exec", "-i", "-u", "postgres", DATABASE, "psql", "-X", "-q", "-v", "ON_ERROR_STOP=1", "-d", "postgres"],
            input=f"ALTER ROLE pathsol_worker LOGIN PASSWORD '{verifier}';\n")
    except subprocess.CalledProcessError as error:
        print(f"FALHA no banco: {error.stderr.strip()}; o cofre já tem uma senha nova: rode de novo", file=sys.stderr)
        return 1
    print("OK senha nova do pathsol_worker: no cofre (banco-worker) e no papel, que agora tem LOGIN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
