"""The worker on VM2 (plan, sections 8.3 and 9.1): one job at a time, until the queue stays idle.

Configured by the environment (the VM2 unit, slice 9):
  PATHSOL_MODELO        directory of the pinned Hibou-L revision, read-only
  PATHSOL_TRABALHO      work root on the temporary disk, emptied at start (test 8)
  PATHSOL_BANCO         libpq conninfo without the password, with sslmode=verify-full
  PATHSOL_VISIBILIDADE  visibility timeout in seconds: twice the worst measured time, at least 1800 (plan 9.1)
  PATHSOL_OCIOSO        seconds without a job before stopping: 600 (plan 8.3)
  PATHSOL_PIOR_JOB      worst measured job time in seconds (plan, section 7)
  PATHSOL_DESLIGA_VM1   VM1's daily shutdown, HH:MM in UTC
  PATHSOL_PULSO         heartbeat file on the host, read by the watchdog (plan 8.3, layer 2)
  PATHSOL_MANUTENCAO    maintenance marker on the host, mounted read-only (pattern 11)
The database password is the Key Vault secret banco-worker, read with VM2's
identity (Pedro's option A of 30/10), and never logged. When the queue stays
idle, VM2 deallocates itself (layer 1), unless a maintenance marker holds.
"""
import contextlib
import datetime
import functools
import json
import logging
import os
import shutil
import threading
import time
from urllib.request import Request, urlopen

import psycopg

from pathsol_worker import banco, blob, consumidor, energia, extractor, fila, identidade, processo, versao

VAULT = "https://vault.azure.net"
SECRET_URL = "https://pathsol-kv-v3.vault.azure.net/secrets/banco-worker?api-version=7.4"
POLL = 15
# The watchdog deallocates after 15 min without a beat.
PULSE = 60

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


def touch(path):
    with open(path, "a"):
        pass
    os.utime(path)


@contextlib.contextmanager
def beating(pulse, limit, every=PULSE):
    """Beats during a job, but never past the visibility timeout: a stuck job goes silent."""
    stop = threading.Event()

    def beat():
        deadline = time.monotonic() + limit
        while not stop.wait(every) and time.monotonic() < deadline:
            pulse()

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        yield
    finally:
        stop.set()
        thread.join()


def run(jobs, dead_letter, store, processor, visibility, idle, pulse=lambda: None, heartbeat=lambda: None,
        accepting=lambda: True, clock=time.monotonic, sleep=time.sleep, handle=consumidor.handle):
    """`pulse` may run in another thread during a job; `heartbeat` uses the job store's connection, so only here."""
    last = clock()
    while True:
        pulse()
        try:
            heartbeat()
        except psycopg.Error as error:
            log.warning("heartbeat no banco: %s", error)
        received = jobs.get(visibility) if accepting() else None
        if received is None:
            if clock() - last >= idle:
                return
            sleep(POLL)
            continue
        try:
            with beating(pulse, visibility):
                log.info("mensagem %s: %s", received.id, handle(received, jobs, dead_letter, store, processor))
        except Exception:  # the message comes back after the visibility timeout
            log.exception("mensagem %s: falha fora do processamento", received.id)
        last = clock()


def leave(marker, now, deallocate=energia.deallocate):
    """After the idle period: VM2 deallocates itself unless a maintenance marker holds."""
    try:
        deadline = energia.maintenance_until(marker, now)
    except ValueError as error:
        log.error("%s: ignorado", error)
        deadline = None
    if deadline:
        log.info("fila ociosa; manutenção até %s: a VM2 fica ligada", deadline.isoformat())
        return None
    status = deallocate()
    log.info("fila ociosa: desalocação da VM2 pedida (HTTP %s)", status)
    return status


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    env = os.environ
    workroot = env["PATHSOL_TRABALHO"]
    empty(workroot)
    pulse = functools.partial(touch, env.get("PATHSOL_PULSO", "/var/lib/pathsol/pulso"))
    pulse()
    worst = int(env.get("PATHSOL_PIOR_JOB", 900))
    shutdown = datetime.time.fromisoformat(env.get("PATHSOL_DESLIGA_VM1", "02:00"))
    model = env["PATHSOL_MODELO"]
    version = versao.extractor_version(model)
    hibou = extractor.Extractor(model, "cuda", "fp16")
    store = banco.JobStore(env["PATHSOL_BANCO"], password=db_password())
    log.info("pronto: extractor_version %s", versao.short_hash(version))
    try:
        run(fila.Queue(fila.JOBS), fila.Queue(fila.DEAD_LETTER), store,
            processo.Processor(blob.Blob(), hibou, version, versao.software(), workroot),
            visibility=int(env.get("PATHSOL_VISIBILIDADE", 1800)), idle=int(env.get("PATHSOL_OCIOSO", 600)),
            pulse=pulse, heartbeat=store.beat,
            accepting=lambda: energia.accepting(datetime.datetime.now(datetime.UTC), worst, shutdown))
    finally:
        store.close()
    leave(env.get("PATHSOL_MANUTENCAO", "/etc/pathsol/manutencao"), datetime.datetime.now(datetime.UTC))
