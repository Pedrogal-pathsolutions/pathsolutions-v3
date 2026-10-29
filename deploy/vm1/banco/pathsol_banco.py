#!/usr/bin/python3
"""Backup, checks and restore test of the v3 database (plan, section 7).

  cria      once, on an empty /srv/banco: directories and initdb
  diario    pgBackRest backup (full weekly, differential otherwise), then
            pg_dump of every database to backup-banco, under dump/<UTC time>/
  verifica  database up, WAL archiving, age of the backup, of the dump and of
            the last restore test, and the two TLS certificates
  restaura  the newest backup, with WAL up to a fresh canary row, and the
            newest dump, each into a scratch cluster on /data

Results go to syslog local0 as "OK <check>: ..." or, with priority err,
"FALHA <check>: ...", which the two log alerts read. Blob Storage is reached
with VM1's system identity, which may read, write and delete only in
backup-banco.
"""
import base64
import datetime
import email.utils
import hashlib
import io
import json
import os
import re
import secrets
import shutil
import socket
import ssl
import struct
import subprocess
import sys
import syslog
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree

CONTAINER_URL = "https://pathsolwsiv3.blob.core.windows.net/backup-banco"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://storage.azure.com/"
)
X_MS_VERSION = "2024-11-04"
BLOCK_SIZE = 64 * 1024 * 1024

IMAGE = "pathsol-banco:18.6-2.60.0"
DATABASE = "pathsol-banco"
STANZA = "pathsol"
POSTGRES_ID = 5432
PGDATA = "/var/lib/postgresql/18/docker"  # inside the container
DATA_ROOT = "/srv/banco/postgresql"
SPOOL = "/srv/banco/pgbackrest-spool"
PGBACKREST_CONF = "/etc/pathsol/banco/pgbackrest.conf"
DB_CERT = "/etc/pathsol/banco/tls/servidor.crt"
APP_NAME = "app.pathsolutions.com.br"
SCRATCH = "/data/pathsol-restauracao"
SCRATCH_CONTAINERS = ("pathsol-restauracao-backup", "pathsol-restauracao-dump")
RESTORE_MARK = "/var/lib/pathsol-banco/restauracao-ok"
# Code point order and Unicode case rules that do not change with glibc, so a
# physical backup restores onto a newer image without reindexing.
INITDB_ARGS = (
    "--username=postgres", "--auth-local=peer", "--auth-host=reject",
    "--encoding=UTF8", "--locale=C.UTF-8", "--locale-provider=builtin", "--builtin-locale=C.UTF-8",
)

HOUR = 3600
DAY = 24 * HOUR
FULL_EVERY = 6 * DAY  # weekly: Monday's run starts seconds before last week's
BACKUP_MAX_AGE = 26 * HOUR
RESTORE_MAX_AGE = 35 * DAY
BOOT_GRACE = 3 * HOUR
CERT_MARGIN = 21 * DAY
ARCHIVE_MAX_WAIT = 10 * 60
RESTORE_SPARE = 5 * 1024**3

WAL_SEGMENT = re.compile(r"[0-9A-F]{24}")
DUMP_RUN = re.compile(r"dump/(\d{8}T\d{6}Z)/completo")


def backup_type(last_full_stop, now):
    """Full when there is none or the last one is 6 days old or more."""
    if last_full_stop is None or now - last_full_stop >= FULL_EVERY:
        return "full"
    return "diff"


def duration(seconds):
    if seconds < 2 * DAY:
        return f"{seconds / HOUR:.1f} h".replace(".", ",")
    return f"{seconds / DAY:.1f} dias".replace(".", ",")


def age_check(name, last, now, uptime, max_age, grace):
    """VM1 is off at night and on weekends: right after boot, an old copy
    only means the day's run has not finished yet."""
    if last is None:
        return False, f"{name}: nenhum encontrado"
    age = now - last
    if age <= max_age:
        return True, f"{name}: o último tem {duration(age)}"
    if uptime < grace:
        return True, f"{name}: o último tem {duration(age)}; a rotina do dia roda depois da partida"
    return False, f"{name}: o último tem {duration(age)}, acima de {duration(max_age)}"


def cert_check(name, not_before, not_after, now):
    """21 days left (plan 4.5) or a quarter of the lifetime, whichever is
    less: Let's Encrypt moves to 64-day certificates in 2027 and renews them
    at about 2/3 of their life, with ~21 days left."""
    margin = min(CERT_MARGIN, (not_after - not_before) / 4)
    left = not_after - now
    days = f"{left / DAY:.1f}".replace(".", ",")
    if left >= margin:
        return True, f"{name}: vence em {days} dias"
    return False, f"{name}: vence em {days} dias, abaixo de {margin / DAY:.0f}"


def archive_check(oldest_ready, now):
    """A segment waiting more than 10 min means pgBackRest is not taking WAL."""
    if oldest_ready is None:
        return True, "arquivamento: nenhum segmento esperando"
    waiting = f"segmento esperando há {(now - oldest_ready) / 60:.0f} min"
    return now - oldest_ready <= ARCHIVE_MAX_WAIT, f"arquivamento: {waiting}"


def wal_dropped(last_archived_wal, repo_max):
    """Past the queue cap, pgBackRest reports WAL as archived without storing
    it, so PostgreSQL counts a segment that the repository lacks."""
    if not last_archived_wal or not repo_max or not WAL_SEGMENT.fullmatch(last_archived_wal):
        return False
    return last_archived_wal > repo_max


def blocks(stream, size):
    while block := stream.read(size):
        yield block


def block_id(index):
    """All block IDs of a blob must have the same length."""
    return base64.b64encode(f"{index:06d}".encode()).decode()


def newest_dump_run(names):
    """dump/<UTC time>/completo is written after every file of its run."""
    return max((m.group(1) for m in map(DUMP_RUN.fullmatch, names) if m), default=None)


def run_time(run):
    moment = datetime.datetime.strptime(run, "%Y%m%dT%H%M%SZ")
    return moment.replace(tzinfo=datetime.timezone.utc).timestamp()


def parse_info(text):
    """What the checks use from `pgbackrest info --output=json`."""
    stanza = json.loads(text)[0]
    backups = stanza["backup"]
    fulls = [b for b in backups if b["type"] == "full"]
    last = backups[-1] if backups else {}
    return {
        "status": (stanza["status"]["code"], stanza["status"]["message"]),
        "last_full_stop": fulls[-1]["timestamp"]["stop"] if fulls else None,
        "last_stop": last.get("timestamp", {}).get("stop"),
        "last_error": last.get("error"),
        "size": last.get("info", {}).get("size"),
        "archive_max": stanza["archive"][-1]["max"] if stanza["archive"] else None,
    }


def globals_errors_ok(stderr):
    """Restoring the roles into a new cluster repeats CREATE ROLE postgres."""
    errors = [line for line in stderr.splitlines() if "ERROR:" in line]
    return all(line.endswith('ERROR:  role "postgres" already exists') for line in errors)


def describe(error):
    """One short line for syslog."""
    if isinstance(error, subprocess.CalledProcessError):
        lines = (error.stderr or error.stdout or "").strip().splitlines()
        text = lines[-1] if lines else f"{error.cmd[0]} saiu com código {error.returncode}"
    else:
        text = str(error)
    return text[:300]


def log(ok, message):
    syslog.syslog(syslog.LOG_INFO if ok else syslog.LOG_ERR, ("OK " if ok else "FALHA ") + message)


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def in_container(container, *args):
    return run(["docker", "exec", "-u", "postgres", container, *args]).stdout


def psql(sql, db="postgres", container=DATABASE):
    return in_container(container, "psql", "-XAtq", "-v", "ON_ERROR_STOP=1", "-d", db, "-c", sql).strip()


def pgbackrest(*args):
    return in_container(DATABASE, "pgbackrest", f"--stanza={STANZA}", *args)


def wait_ready(container=DATABASE, timeout=300):
    """At boot the timers can start before the database takes connections."""
    deadline = time.monotonic() + timeout
    while subprocess.run(["docker", "exec", "-u", "postgres", container, "pg_isready", "-q"], capture_output=True).returncode:
        if time.monotonic() > deadline:
            raise RuntimeError(f"{container} não aceitou conexões em {timeout} s")
        time.sleep(5)


def owned_dir(path):
    os.makedirs(path, 0o700)
    os.chown(path, POSTGRES_ID, POSTGRES_ID)
    return path


class Blob:
    def __init__(self):
        request = urllib.request.Request(IMDS_TOKEN_URL, headers={"Metadata": "true"})
        with urllib.request.urlopen(request, timeout=10) as response:
            self.token = json.load(response)["access_token"]

    def request(self, method, name="", query="", headers=None, data=None):
        url = CONTAINER_URL + (f"/{urllib.parse.quote(name)}" if name else "") + (f"?{query}" if query else "")
        headers = {
            "Authorization": f"Bearer {self.token}",
            "x-ms-version": X_MS_VERSION,
            "x-ms-date": email.utils.formatdate(usegmt=True),
            **(headers or {}),
        }
        for attempt in (1, 2, 3):
            try:
                return urllib.request.urlopen(urllib.request.Request(url, data, headers, method=method), timeout=300)
            except urllib.error.HTTPError as error:
                if error.code < 500 or attempt == 3:
                    raise
            except OSError:
                if attempt == 3:
                    raise
            time.sleep(10 * attempt)

    def put_blocks(self, name, stream):
        """Uncommitted blocks stay invisible and expire in 7 days."""
        ids, total = [], hashlib.md5()
        for index, block in enumerate(blocks(stream, BLOCK_SIZE)):
            ids.append(block_id(index))
            md5 = base64.b64encode(hashlib.md5(block).digest()).decode()
            self.request("PUT", name, f"comp=block&blockid={urllib.parse.quote(ids[-1])}", {"Content-MD5": md5}, block).close()
            total.update(block)
        return ids, base64.b64encode(total.digest()).decode()

    def commit(self, name, ids, md5):
        """If-None-Match: * makes the blob appear once, whole, and never
        replaces an existing one."""
        body = "<?xml version='1.0' encoding='utf-8'?><BlockList>" + "".join(f"<Latest>{i}</Latest>" for i in ids) + "</BlockList>"
        headers = {"If-None-Match": "*", "x-ms-blob-content-md5": md5, "Content-Type": "application/xml"}
        self.request("PUT", name, "comp=blocklist", headers, body.encode()).close()

    def list(self, prefix):
        names, marker = [], ""
        while True:
            query = f"restype=container&comp=list&prefix={urllib.parse.quote(prefix)}"
            if marker:
                query += f"&marker={urllib.parse.quote(marker)}"
            with self.request("GET", query=query) as response:
                root = ElementTree.parse(response).getroot()
            names += [element.text for element in root.iter("Name")]
            marker = root.findtext("NextMarker")
            if not marker:
                return names

    def download(self, name, path):
        total = hashlib.md5()
        with self.request("GET", name) as response, open(path, "wb") as file:
            while chunk := response.read(BLOCK_SIZE):
                file.write(chunk)
                total.update(chunk)
            expected = response.headers["Content-MD5"]
        if base64.b64encode(total.digest()).decode() != expected:
            raise RuntimeError(f"{name}: o MD5 não bate com o gravado")


def https_cert(port, name):
    context = ssl.create_default_context()
    with socket.create_connection(("127.0.0.1", port), timeout=10) as raw:
        with context.wrap_socket(raw, server_hostname=name) as tls:
            return cert_dates(tls.getpeercert())


def postgres_cert(port, cafile):
    """PostgreSQL answers an SSLRequest before the TLS handshake."""
    context = ssl.create_default_context(cafile=cafile)
    with socket.create_connection(("127.0.0.1", port), timeout=10) as raw:
        raw.sendall(struct.pack("!ii", 8, 80877103))
        if raw.recv(1) != b"S":
            raise RuntimeError("o banco recusou TLS")
        with context.wrap_socket(raw, server_hostname="127.0.0.1") as tls:
            return cert_dates(tls.getpeercert())


def cert_dates(cert):
    return ssl.cert_time_to_seconds(cert["notBefore"]), ssl.cert_time_to_seconds(cert["notAfter"])


def initdb(root, network):
    run(["docker", "run", "--rm", "--pull", "never", "--network", network, "--user", "postgres",
         "-v", f"{root}:/var/lib/postgresql", IMAGE, "initdb", "-D", PGDATA, *INITDB_ARGS])


def cria():
    """os.makedirs refuses existing directories: this never touches a cluster."""
    owned_dir(DATA_ROOT)
    owned_dir(SPOOL)
    initdb(DATA_ROOT, "none")
    log(True, f"cria: cluster novo em {DATA_ROOT}")
    return True


def ensure_canary():
    """The restore test checks its rows in the backup and in the dump."""
    if not psql("select 1 from pg_database where datname = 'canario'"):
        psql("create database canario")
    psql("create table if not exists restauracao (token text primary key, criado_em timestamptz not null default now())", "canario")


def backup():
    wait_ready()
    info = parse_info(pgbackrest("info", "--output=json"))
    kind = backup_type(info["last_full_stop"], time.time())
    start = time.monotonic()
    pgbackrest(f"--type={kind}", "backup")
    return f"{kind} em {time.monotonic() - start:.0f} s"


def dump():
    wait_ready()
    ensure_canary()
    run_name = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    databases = psql("select datname from pg_database where datallowconn and not datistemplate order by 1").split()
    files = [("globais.sql", ["pg_dumpall", "--globals-only"])]
    files += [(f"{db}.dump", ["pg_dump", "--format=custom", "--compress=zstd", f"--dbname={db}"]) for db in databases]
    blob = Blob()
    for name, command in files:
        # stderr goes to the journal; stdout is only read here.
        process = subprocess.Popen(["docker", "exec", "-u", "postgres", DATABASE, *command], stdout=subprocess.PIPE)
        ids, md5 = blob.put_blocks(f"dump/{run_name}/{name}", process.stdout)
        if process.wait():
            raise RuntimeError(f"{command[0]} de {name} saiu com código {process.returncode}")
        blob.commit(f"dump/{run_name}/{name}", ids, md5)
    summary = io.BytesIO(json.dumps({"arquivos": [name for name, _ in files]}).encode())
    blob.commit(f"dump/{run_name}/completo", *blob.put_blocks(f"dump/{run_name}/completo", summary))
    return f"dump/{run_name}/, {len(files)} arquivos"


def step(name, action):
    try:
        log(True, f"{name}: {action()}")
        return True
    except Exception as error:  # every failure must reach syslog
        log(False, f"{name}: {describe(error)}")
        return False


def diario():
    backed_up = step("backup", backup)
    dumped = step("dump", dump)
    return backed_up and dumped


def check_database(now, uptime):
    oldest = psql("select extract(epoch from min(modification)) from pg_ls_archive_statusdir() where name like '%.ready'")
    return [(True, "banco: aceita conexões"), archive_check(float(oldest) if oldest else None, now)]


def check_backup(now, uptime):
    info = parse_info(pgbackrest("info", "--output=json"))
    code, message = info["status"]
    if code:
        return [(False, f"backup: pgBackRest diz {message}")]
    results = [age_check("backup", info["last_stop"], now, uptime, BACKUP_MAX_AGE, BOOT_GRACE)]
    if info["last_error"]:
        results.append((False, "backup: o último achou página com checksum inválido"))
    archived = psql("select coalesce(last_archived_wal, '') from pg_stat_archiver")
    if wal_dropped(archived, info["archive_max"]):
        results.append((False, f"arquivamento: {archived} dado por arquivado, e o repositório para em {info['archive_max']}"))
    return results


def check_dump(now, uptime):
    run_name = newest_dump_run(Blob().list("dump/"))
    return [age_check("dump", run_time(run_name) if run_name else None, now, uptime, BACKUP_MAX_AGE, BOOT_GRACE)]


def check_certs(now, uptime):
    return [
        cert_check("certificado-app", *https_cert(443, APP_NAME), now),
        cert_check("certificado-banco", *postgres_cert(5432, DB_CERT), now),
    ]


def check_restore(now, uptime):
    last = os.path.getmtime(RESTORE_MARK) if os.path.exists(RESTORE_MARK) else None
    return [age_check("restauracao", last, now, uptime, RESTORE_MAX_AGE, BOOT_GRACE)]


def verifica():
    now = time.time()
    with open("/proc/uptime") as file:
        uptime = float(file.read().split()[0])
    results = []
    checks = (("banco", check_database), ("backup", check_backup), ("dump", check_dump),
              ("certificados", check_certs), ("restauracao", check_restore))
    for name, check in checks:
        try:
            results += check(now, uptime)
        except Exception as error:  # one broken check must not hide the others
            results.append((False, f"{name}: {describe(error)}"))
    for ok, message in results:
        log(ok, message)
    return all(ok for ok, _ in results)


def canary():
    """A fresh row, then `pgbackrest check`, which switches WAL and waits for
    the segment to reach the repository."""
    ensure_canary()
    token = secrets.token_hex(16)
    psql(f"insert into restauracao (token) values ('{token}')", "canario")
    pgbackrest("check")
    return token


def restore_backup(token):
    root = owned_dir(f"{SCRATCH}/backup")
    owned_dir(f"{root}/18/docker")
    mounts = ["-v", f"{root}:/var/lib/postgresql", "-v", f"{PGBACKREST_CONF}:/etc/pgbackrest/pgbackrest.conf:ro"]
    name = SCRATCH_CONTAINERS[0]
    # Bridge network, no published port: the same IMDS path the worker uses.
    run(["docker", "run", "--rm", "--pull", "never", "--user", "postgres", *mounts, IMAGE,
         "pgbackrest", f"--stanza={STANZA}", "--archive-mode=off", "restore"])
    run(["docker", "run", "-d", "--rm", "--pull", "never", "--name", name, "--user", "postgres", *mounts, IMAGE,
         "postgres", "-c", "listen_addresses=", "-c", "archive_mode=off"])
    wait_ready(name, timeout=600)
    deadline = time.monotonic() + 600
    while psql("select pg_is_in_recovery()", container=name) == "t":
        if time.monotonic() > deadline:
            raise RuntimeError("a recuperação não terminou em 600 s")
        time.sleep(5)
    found = psql(f"select count(*) from restauracao where token = '{token}'", "canario", name)
    rows = psql("select count(*) from restauracao", "canario", name)
    run(["docker", "stop", name])
    if found != "1" or rows != psql("select count(*) from restauracao", "canario"):
        raise RuntimeError(f"backup restaurado sem a linha nova ou com {rows} linhas")
    return rows


def restore_dump():
    blob = Blob()
    run_name = newest_dump_run(blob.list("dump/"))
    if not run_name:
        raise RuntimeError("nenhum dump completo")
    files_dir = owned_dir(f"{SCRATCH}/dump")
    for name in blob.list(f"dump/{run_name}/"):
        path = f"{files_dir}/{name.rsplit('/', 1)[1]}"
        blob.download(name, path)
        os.chown(path, POSTGRES_ID, POSTGRES_ID)
    root = owned_dir(f"{SCRATCH}/cluster-dump")
    initdb(root, "none")
    name = SCRATCH_CONTAINERS[1]
    run(["docker", "run", "-d", "--rm", "--pull", "never", "--network", "none", "--name", name, "--user", "postgres",
         "-v", f"{root}:/var/lib/postgresql", "-v", f"{files_dir}:/restauracao:ro", IMAGE, "postgres", "-c", "listen_addresses="])
    wait_ready(name)
    roles = subprocess.run(["docker", "exec", "-u", "postgres", name, "psql", "-X", "-q", "-f", "/restauracao/globais.sql"],
                           capture_output=True, text=True)
    if roles.returncode or not globals_errors_ok(roles.stderr):
        raise RuntimeError(f"globais.sql: {roles.stderr.strip().splitlines()[-1]}")
    for file in sorted(os.listdir(files_dir)):
        if file.endswith(".dump"):
            # pg_restore -C creates each database; postgres already exists.
            target = [] if file == "postgres.dump" else ["--create"]
            in_container(name, "pg_restore", "--exit-on-error", *target, "--dbname=postgres", f"/restauracao/{file}")
    rows = psql("select count(*) from restauracao", "canario", name)
    run(["docker", "stop", name])
    expected = psql(f"select count(*) from restauracao where criado_em < to_timestamp({run_time(run_name)})", "canario")
    if rows != expected:
        raise RuntimeError(f"dump {run_name} restaurado com {rows} linhas, e eram {expected}")
    return run_name


def clean():
    for name in SCRATCH_CONTAINERS:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    shutil.rmtree(SCRATCH, ignore_errors=True)


def restore():
    wait_ready()
    size = parse_info(pgbackrest("info", "--output=json"))["size"]
    if size is None:
        raise RuntimeError("nenhum backup")
    if shutil.disk_usage("/data").free < 2 * size + RESTORE_SPARE:
        raise RuntimeError(f"/data sem espaço para duas cópias de {size / 1024**3:.1f} GiB")
    clean()
    try:
        owned_dir(SCRATCH)
        token = canary()
        rows = restore_backup(token)
        run_name = restore_dump()
    finally:
        clean()
    with open(RESTORE_MARK, "w") as file:
        file.write(f"{token}\n")
    return f"backup com WAL até a linha nova ({rows} linhas) e dump {run_name}"


def restaura():
    return step("restauracao", restore)


COMMANDS = {"cria": cria, "diario": diario, "verifica": verifica, "restaura": restaura}


def main(argv):
    if len(argv) != 2 or argv[1] not in COMMANDS:
        sys.exit("usage: pathsol-banco " + "|".join(COMMANDS))
    syslog.openlog("pathsol-banco", 0, syslog.LOG_LOCAL0)
    sys.exit(0 if COMMANDS[argv[1]]() else 1)


if __name__ == "__main__":
    main(sys.argv)
