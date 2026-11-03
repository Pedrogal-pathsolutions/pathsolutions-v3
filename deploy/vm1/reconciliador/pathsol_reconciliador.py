#!/usr/bin/python3
"""Reconciler of VM2, the GPU worker, on VM1 (plan, sections 7, 8.3 and 9.4).

Installed as /usr/local/sbin/pathsol-reconciliador; its timer runs one pass
every 30 s while VM1 is on, and each pass decides at most one action:
  start       a job is visible; VM2 is deallocated or stopped; the oldest job
              waited PATHSOL_ESPERA_PARTIDA (pattern 10); and VM2, ready in
              300 s, would finish the worst measured job, PATHSOL_PIOR_JOB,
              before VM1's next auto-shutdown, PATHSOL_DESLIGA_VM1 (plan 7)
  deallocate  layer 3 of plan 8.3: no job visible, VM2 running for longer
              than the visibility timeout, PATHSOL_VISIBILIDADE, and the
              worker's heartbeat older than it, even with a job RUNNING in
              the database: its message comes back after the timeout
A valid maintenance marker holds both: /etc/pathsol/manutencao-vm2, one line
with a UTC deadline (YYYY-MM-DDTHH:MM:SSZ) at most 4 h after the file was
written. The age of the oldest visible job is logged on every pass that sees
one, for the alarm of plan 9.4.

Lines go to syslog local0 as "OK ..." or, with priority err, "FALHA ...",
and none when there is nothing to do; the exit code is 1 after any FALHA.
Calls go out with VM1's system identity, whose VM role reaches only VM2; the
queue is only peeked, and the message text is never looked at.
"""
import datetime
import email.utils
import json
import os
import re
import subprocess
import sys
import syslog
from urllib.request import Request, urlopen
from xml.etree import ElementTree

VM2_URL = (
    "https://management.azure.com/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1"
    "/resourceGroups/rg-prod-brsouth-001/providers/Microsoft.Compute/virtualMachines/vm-appfoundation-prod-001"
)
COMPUTE_API = "api-version=2025-04-01"
QUEUE_PEEK_URL = "https://pathsolwsiv3.queue.core.windows.net/jobs/messages?peekonly=true&numofmessages=1"
IMDS_TOKEN_URL = "http://169.254.169.254/metadata/identity/oauth2/token?api-version=2018-02-01&resource="
ARM = "https://management.azure.com/"
STORAGE = "https://storage.azure.com/"
X_MS_VERSION = "2024-11-04"
HEARTBEAT_AGE = [
    "docker", "exec", "-u", "postgres", "pathsol-banco", "psql", "-X", "-At", "-d", "pathsol",
    "-c", "select extract(epoch from now() - max(beat_at))::bigint from worker_heartbeat",
]
MARKER = "/etc/pathsol/manutencao-vm2"
MARKER_MAX_HOURS = 4  # plan 8.3: maintenance has a maximum term

# Defaults of the unit's environment; durations in seconds.
VISIBILITY = 1800  # visibility timeout, at least 30 min (plan 9.1)
WORST_JOB = 900  # worst measured job, provisional until the acceptance tests
START_WAIT = 900  # production; 0 while building (pattern 10)
VM1_SHUTDOWN = "02:00"  # UTC: 23:00 in Brasilia (decision 3)

WORKER_READY = 300  # seconds from the start until the worker takes jobs
# Never during a transition: a start sent while VM2 was deallocating was
# accepted and won (Phase 3, slice 8).
START_FROM = ("deallocated", "stopped")
# On 30/10 the platform reached VM1's guest at 02:02:03 for a 02:00 shutdown;
# until then the timer keeps running and must not take tomorrow's shutdown as
# the next one.
SHUTDOWN_GRACE = datetime.timedelta(minutes=10)
UTC = datetime.timezone.utc
ARM_TIME = re.compile(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d)(?:\.(\d+))?(Z|[+-]\d\d:\d\d)")


def log(ok, text):
    syslog.syslog(syslog.LOG_INFO if ok else syslog.LOG_ERR, ("OK " if ok else "FALHA ") + text)


def describe(error):
    """One short line for syslog."""
    if isinstance(error, subprocess.CalledProcessError):
        lines = (error.stderr or "").strip().splitlines()
        text = lines[0] if lines else f"{error.cmd[0]} saiu com código {error.returncode}"
    else:
        text = str(error) or type(error).__name__
    return text[:300]


def step(what, action, *args):
    """Runs one step; any failure comes out as one line that names the step."""
    try:
        return action(*args)
    except Exception as error:
        raise RuntimeError(f"{what}: {describe(error)}") from error


def utc_text(moment):
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def arm_time(text):
    """ARM writes 7 fractional digits; strptime takes up to 6, and fromisoformat
    takes 7 only from Python 3.11."""
    match = ARM_TIME.fullmatch(text)
    if not match:
        raise ValueError(f"hora fora do ISO 8601: {text}")
    base, fraction, zone = match.groups()
    return datetime.datetime.strptime(f"{base}.{(fraction or '0')[:6]}{zone}", "%Y-%m-%dT%H:%M:%S.%f%z")


def read_rules(env):
    return (
        int(env.get("PATHSOL_VISIBILIDADE", VISIBILITY)),
        int(env.get("PATHSOL_PIOR_JOB", WORST_JOB)),
        int(env.get("PATHSOL_ESPERA_PARTIDA", START_WAIT)),
        datetime.datetime.strptime(env.get("PATHSOL_DESLIGA_VM1", VM1_SHUTDOWN), "%H:%M").time(),
    )


def read_marker(path, now):
    """(deadline, problem): the deadline of a valid marker, or why an existing one is ignored."""
    try:
        with open(path, encoding="utf-8") as file:
            text = file.read()
            written = datetime.datetime.fromtimestamp(os.fstat(file.fileno()).st_mtime, UTC)
    except FileNotFoundError:
        return None, None
    except (OSError, ValueError) as error:  # UnicodeDecodeError is a ValueError
        return None, f"marcador de manutenção {path} ilegível ({describe(error)}); ignorado"
    try:
        deadline = datetime.datetime.strptime(text.removesuffix("\n"), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return None, f"marcador de manutenção {path} fora do formato AAAA-MM-DDTHH:MM:SSZ; ignorado"
    if deadline <= now:
        return None, f"marcador de manutenção {path} vencido em {utc_text(deadline)}; ignorado"
    if deadline > written + datetime.timedelta(hours=MARKER_MAX_HOURS):
        return None, (f"marcador de manutenção {path} até {utc_text(deadline)}, mais de {MARKER_MAX_HOURS} h "
                      f"depois de gravado ({utc_text(written)}); ignorado")
    return deadline, None


def token(resource, opener):
    with opener(Request(IMDS_TOKEN_URL + resource, headers={"Metadata": "true"}), timeout=10) as response:
        return json.load(response)["access_token"]


def oldest_job(queue_token, opener):
    """InsertionTime of the oldest visible message, or None. A peek changes
    nothing in the queue, and only InsertionTime is taken from the answer."""
    request = Request(QUEUE_PEEK_URL, headers={
        "Authorization": f"Bearer {queue_token}",
        "x-ms-version": X_MS_VERSION,
        "x-ms-date": email.utils.formatdate(usegmt=True),
    })
    with opener(request, timeout=30) as response:
        inserted = ElementTree.fromstring(response.read()).findtext("QueueMessage/InsertionTime")
    return None if inserted is None else email.utils.parsedate_to_datetime(inserted)


def vm2_state(arm_token, opener):
    """PowerState of VM2 and when its last operation succeeded, which for a
    running VM2 is its start; None while another operation is under way."""
    request = Request(f"{VM2_URL}/instanceView?{COMPUTE_API}", headers={"Authorization": f"Bearer {arm_token}"})
    with opener(request, timeout=30) as response:
        statuses = {status["code"]: status.get("time") for status in json.load(response)["statuses"]}
    powers = [code.split("/", 1)[1] for code in statuses if code.startswith("PowerState/")]
    if len(powers) != 1:
        raise ValueError(f"instanceView com {len(powers)} PowerState")
    since = statuses.get("ProvisioningState/succeeded")
    return powers[0], arm_time(since) if since else None


def vm2_action(action, arm_token, opener):
    """start or deallocate: ARM answers 202 and carries on by itself."""
    # Without data, http.client sends Content-Length: 0, the empty body ARM takes.
    request = Request(f"{VM2_URL}/{action}?{COMPUTE_API}", method="POST", headers={"Authorization": f"Bearer {arm_token}"})
    with opener(request, timeout=30) as response:
        return response.status


def run(args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=30)


def heartbeat_age(run):
    """Seconds since the worker's last beat; None if it never beat."""
    out = run(HEARTBEAT_AGE).stdout.strip()
    return int(out) if out else None


def next_shutdown(now, at):
    """VM1's next auto-shutdown at `at` (UTC); one that began less than
    SHUTDOWN_GRACE ago is still the next."""
    after = now - SHUTDOWN_GRACE
    shutdown = datetime.datetime.combine(after.date(), at, tzinfo=UTC)
    return shutdown if shutdown > after else shutdown + datetime.timedelta(days=1)


def reconcile(now, uptime, env, marker, opener, run):
    """One pass. Returns False when anything failed; each failure is logged once."""
    try:
        deadline, problem = read_marker(marker, now)
        if problem:
            log(False, problem)
        if deadline:
            log(True, f"manutenção até {utc_text(deadline)}")
        visibility, worst_job, start_wait, vm1_shutdown = step("variáveis da unit", read_rules, env)
        queue_token = step("token do IMDS para a fila", token, STORAGE, opener)
        inserted = step("peek da fila jobs", oldest_job, queue_token, opener)
        if inserted is not None:
            waited = (now - inserted).total_seconds()
            # Plan 9.4 counts only VM1's hours: a job from the night before
            # must not raise the alarm as soon as VM1 starts.
            log(True, f"idade do job mais antigo: {max(0, int(min(waited, uptime)))} s")
        if deadline:
            return True
        arm_token = step("token do IMDS para a ARM", token, ARM, opener)
        power, since = step("instanceView da VM2", vm2_state, arm_token, opener)
        if inserted is not None:
            if power in START_FROM and waited >= start_wait:
                shutdown = next_shutdown(now, vm1_shutdown)
                if now + datetime.timedelta(seconds=WORKER_READY + worst_job) < shutdown:
                    status = step("start da VM2", vm2_action, "start", arm_token, opener)
                    log(True, f"start da VM2 pedido (HTTP {status}): estava {power}, e o job mais antigo espera há {int(waited)} s")
                else:
                    log(True, f"partida da VM2 adiada: {WORKER_READY} s até o worker pronto e {worst_job} s do pior job "
                              f"passam do desligamento da VM1 em {utc_text(shutdown)}")
        elif power == "running" and since is not None and (now - since).total_seconds() > visibility:
            beat = step("heartbeat do worker, desalocação adiada", heartbeat_age, run)
            if beat is None or beat > visibility:
                status = step("deallocate da VM2", vm2_action, "deallocate", arm_token, opener)
                heartbeat = "nenhum heartbeat" if beat is None else f"heartbeat de {beat} s"
                log(True, f"deallocate da VM2 pedido (HTTP {status}): nenhum job visível, ligada desde "
                          f"{utc_text(since)} e {heartbeat}")
    except Exception as error:  # every failure must reach syslog
        log(False, describe(error))
        return False
    return problem is None


def main():
    syslog.openlog("pathsol-reconciliador", 0, syslog.LOG_LOCAL0)
    with open("/proc/uptime") as file:
        uptime = float(file.read().split()[0])
    sys.exit(0 if reconcile(datetime.datetime.now(UTC), uptime, os.environ, MARKER, urlopen, run) else 1)


if __name__ == "__main__":
    main()
