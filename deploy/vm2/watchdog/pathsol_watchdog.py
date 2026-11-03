#!/usr/bin/python3
"""Watchdog on VM2's host (plan, section 8.3): the second of the three layers
that deallocate VM2, and the one that needs nothing from VM1, which may be off.

One pass per run of pathsol-watchdog.timer:
  - a valid maintenance marker holds every action;
  - for the first 5 min after boot (boot and model load), nothing;
  - from 5 to 15 min, nvidia-smi must name the GPU within 60 s;
  - from 15 min on, the worker must have touched its pulse file since boot
    and within the last 15 min.
Otherwise VM2 is deallocated through ARM with its own identity
(pathsol-vm2-autodesalocar-v3), never stopped from the OS: a VM stopped from
inside keeps billing (plan 8.1). The marker holds one line, a UTC deadline
YYYY-MM-DDTHH:MM:SSZ at most 4 h after the file was written.

Actions and maintenance passes go to syslog local0 as "OK ...", failures with
priority err as "FALHA ...".
"""
import datetime
import json
import os
import re
import subprocess
import sys
import syslog
import time
import urllib.error
from urllib.request import Request, urlopen

VM2_ID = (
    "/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1/resourceGroups/rg-prod-brsouth-001"
    "/providers/Microsoft.Compute/virtualMachines/vm-appfoundation-prod-001"
)
DEALLOCATE_URL = f"https://management.azure.com{VM2_ID}/deallocate?api-version=2025-04-01"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://management.azure.com/"
)
MARKER = "/etc/pathsol/manutencao"
PULSE = "/var/lib/pathsol/pulso"
UPTIME = "/proc/uptime"
GPU_CHECK = ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"]
GPU_TIMEOUT = 60

BOOT_GRACE = 5 * 60
# Plan 8.3: 15 min without a heartbeat, counted from boot when there was none
# since; until then only the GPU is checked.
HEARTBEAT_LIMIT = 15 * 60
MARKER_MAX_TERM = 4 * 3600
MARKER_LINE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z\n?")


class InvalidMarker(Exception):
    pass


def log(ok, message):
    syslog.syslog(syslog.LOG_INFO if ok else syslog.LOG_ERR, ("OK " if ok else "FALHA ") + message)


def deadline_time(text):
    """Epoch of the marker's one line; ValueError for anything else."""
    if not MARKER_LINE.fullmatch(text):
        raise ValueError(text)
    moment = datetime.datetime.strptime(text.rstrip("\n"), "%Y-%m-%dT%H:%M:%SZ")
    return moment.replace(tzinfo=datetime.timezone.utc).timestamp()


def maintenance_deadline(now):
    """The deadline of a valid marker, or None when there is no marker."""
    try:
        with open(MARKER, encoding="utf-8") as file:
            text, written = file.read(), os.fstat(file.fileno()).st_mtime
    except FileNotFoundError:
        return None
    except (OSError, UnicodeError) as error:
        raise InvalidMarker(f"marcador ilegível ({error})") from error
    try:
        end = deadline_time(text)
    except ValueError:
        raise InvalidMarker("marcador sem um prazo válido no formato AAAA-MM-DDTHH:MM:SSZ") from None
    deadline = text.rstrip("\n")
    if end <= now:
        raise InvalidMarker(f"marcador vencido em {deadline}")
    if end > written + MARKER_MAX_TERM:
        raise InvalidMarker(f"prazo {deadline} a mais de 4 h da gravação do marcador")
    return deadline


def gpu_problem():
    """None when nvidia-smi names the GPU in time; otherwise what went wrong."""
    try:
        process = subprocess.Popen(GPU_CHECK, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors="replace")
    except OSError as error:
        return f"nvidia-smi não rodou: {error}"
    try:
        out, err = process.communicate(timeout=GPU_TIMEOUT)
    except subprocess.TimeoutExpired:
        # A failing GPU can hold nvidia-smi in the driver, where SIGKILL never
        # lands: waiting for it would keep VM2 on.
        process.kill()
        return f"nvidia-smi sem resposta em {GPU_TIMEOUT} s"
    if process.returncode:
        lines = (err.strip() or out.strip()).splitlines()
        return f"nvidia-smi saiu com código {process.returncode}" + (f": {lines[-1][:200]}" if lines else "")
    if not out.strip():
        return "nvidia-smi não listou nenhuma GPU"
    return None


def deallocation_reason(now, uptime):
    """Why VM2 must be deallocated now, or None."""
    if uptime < BOOT_GRACE:
        return None
    if uptime < HEARTBEAT_LIMIT:
        problem = gpu_problem()
        return f"GPU falhando na partida ({problem})" if problem else None
    try:
        beat = os.stat(PULSE).st_mtime
    except FileNotFoundError:
        beat = None
    if beat is None or beat < now - uptime:
        return "sem heartbeat desde a partida"
    if now - beat > HEARTBEAT_LIMIT:
        return f"heartbeat parado há {now - beat:.0f} s"
    return None


def request_deallocation(reason):
    """POST without a body; ARM runs it asynchronously, and it is not polled.
    True when ARM accepted."""
    try:
        with urlopen(Request(IMDS_TOKEN_URL, headers={"Metadata": "true"}), timeout=10) as response:
            token = json.load(response)["access_token"]
    except Exception as error:  # every failure must reach syslog
        log(False, f"desalocação: {reason}; token do IMDS: {error}")
        return False
    request = Request(DEALLOCATE_URL, method="POST", headers={"Authorization": f"Bearer {token}"})
    try:
        with urlopen(request, timeout=30) as response:
            status = response.status
    except urllib.error.HTTPError as error:
        log(False, f"desalocação: {reason}; ARM respondeu {error.code}")
        return False
    except Exception as error:  # every failure must reach syslog
        log(False, f"desalocação: {reason}; ARM: {error}")
        return False
    log(True, f"desalocação pedida: {reason}; ARM respondeu {status}")
    return True


def watch(now, uptime):
    """One pass; True when it logged no failure."""
    marker_ok = True
    try:
        deadline = maintenance_deadline(now)
    except InvalidMarker as error:
        log(False, f"manutenção: {error}; ignorado")
        marker_ok, deadline = False, None
    if deadline:
        log(True, f"manutenção até {deadline}")
        return True
    reason = deallocation_reason(now, uptime)
    return (request_deallocation(reason) if reason else True) and marker_ok


def main():
    syslog.openlog("pathsol-watchdog", 0, syslog.LOG_LOCAL0)
    try:
        with open(UPTIME) as file:
            uptime = float(file.read().split()[0])
        ok = watch(time.time(), uptime)
    except Exception as error:  # every failure must reach syslog
        log(False, f"watchdog: {error}")
        ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
