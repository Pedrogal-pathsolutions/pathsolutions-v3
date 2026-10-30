"""The worker on VM2 (plan, sections 8.3 and 9.1): one job at a time, until the queue stays idle.

Configured by the environment (the VM2 unit, slice 9):
  PATHSOL_MODELO        directory of the pinned Hibou-L revision, read-only
  PATHSOL_TRABALHO      work root on the temporary disk, emptied at start (test 8)
  PATHSOL_BANCO         libpq conninfo without the password, with sslmode=verify-full
  PATHSOL_VISIBILIDADE  visibility timeout in seconds: twice the worst measured time, at least 1800 (plan 9.1)
  PATHSOL_OCIOSO        seconds without a job before stopping: 600 (plan 8.3)
The database password is the Key Vault secret banco-worker, read with VM2's
identity (Pedro's option A of 30/10), and never logged.
"""
import json
import logging
import os
import shutil
import time
from urllib.request import Request, urlopen

from pathsol_worker import banco, blob, consumidor, extractor, fila, identidade, processo, versao

VAULT = "https://vault.azure.net"
SECRET_URL = "https://pathsol-kv-v3.vault.azure.net/secrets/banco-worker?api-version=7.4"
POLL = 15

log = logging.getLogger("pathsol_worker")


def db_password(opener=urlopen):
    token = identidade.Token(VAULT, opener)
    with opener(Request(SECRET_URL, headers={"Authorization": f"Bearer {token()}"}), timeout=30) as response:
        return json.load(response)["value"]


def empty(root):
    for name in os.listdir(root):
        path = os.path.join(root, name)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def run(jobs, dead_letter, store, processor, visibility, idle, clock=time.monotonic, sleep=time.sleep,
        handle=consumidor.handle):
    last = clock()
    while True:
        received = jobs.get(visibility)
        if received is None:
            if clock() - last >= idle:
                return
            sleep(POLL)
            continue
        try:
            log.info("mensagem %s: %s", received.id, handle(received, jobs, dead_letter, store, processor))
        except Exception:  # the message comes back after the visibility timeout
            log.exception("mensagem %s: falha fora do processamento", received.id)
        last = clock()


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    env = os.environ
    workroot = env["PATHSOL_TRABALHO"]
    empty(workroot)
    model = env["PATHSOL_MODELO"]
    version = versao.extractor_version(model)
    hibou = extractor.Extractor(model, "cuda", "fp16")
    store = banco.JobStore(env["PATHSOL_BANCO"], password=db_password())
    log.info("pronto: extractor_version %s", versao.short_hash(version))
    try:
        run(fila.Queue(fila.JOBS), fila.Queue(fila.DEAD_LETTER), store,
            processo.Processor(blob.Blob(), hibou, version, versao.software(), workroot),
            visibility=int(env.get("PATHSOL_VISIBILIDADE", 1800)), idle=int(env.get("PATHSOL_OCIOSO", 600)))
    finally:
        store.close()
