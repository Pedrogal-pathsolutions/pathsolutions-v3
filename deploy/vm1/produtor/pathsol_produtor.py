#!/usr/bin/python3
"""Test job producer of Phase 4 (decision 7). Runs only on VM1, by the
operator, with no network port, and leaves the code in Phase 5.

    pathsol_produtor.py tenant SLUG
    pathsol_produtor.py lamina --tenant SLUG --arquivo UUID.svs --sha256 HEX --material M --coloracao C [--orgao O]
    pathsol_produtor.py job --tenant SLUG --lamina UUID [--versao-pipeline V]

The tenant comes from the operator: the one approved exception to "tenant
only from the JWT". Slide and job are written as pathsol_produtor, under RLS,
by psql inside the database container. The message is built from the
database's values and goes to the queue with VM1's identity only after the
commit, so the worker never gets a job that is not in the database.
"""
import argparse
import email.utils
import json
import re
import subprocess
import sys
import urllib.error
import uuid
from urllib.request import Request, urlopen
from xml.sax.saxutils import escape

DATABASE = "pathsol-banco"
QUEUE_URL = "https://pathsolwsiv3.queue.core.windows.net/jobs/messages"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://storage.azure.com/"
)
X_MS_VERSION = "2024-11-04"
UUID = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

AS_PRODUCER = r"""BEGIN;
SELECT id AS tenant FROM tenants WHERE slug = :'slug' \gset
SET LOCAL ROLE pathsol_produtor;
SELECT set_config('app.tenant_id', :'tenant', true) \g /dev/null
"""
TENANT_SQL = """INSERT INTO tenants (id, slug) VALUES (:'id', :'slug') ON CONFLICT (slug) DO NOTHING;
SELECT id FROM tenants WHERE slug = :'slug';
"""
SLIDE_SQL = AS_PRODUCER + """INSERT INTO slides (tenant_id, id, wsi_name, wsi_sha256, organ, material, stain)
VALUES (:'tenant', :'slide', :'nome', :'sha256', NULLIF(:'orgao', ''), :'material', :'coloracao');
COMMIT;
"""
JOB_SQL = AS_PRODUCER + r"""SELECT wsi_name, coalesce(organ, '') AS organ, material FROM slides WHERE id = :'slide' \gset
INSERT INTO jobs (tenant_id, id, slide_id, pipeline_version) VALUES (:'tenant', :'job', :'slide', :'versao');
COMMIT;
SELECT :'tenant' || '|' || :'wsi_name' || '|' || :'organ' || '|' || :'material';
"""


def checked(regex, what):
    def check(value):
        if not re.fullmatch(regex, value):
            raise argparse.ArgumentTypeError(f"{what} inválido")
        return value
    return check


def run(args, **kwargs):
    return subprocess.run(args, check=True, capture_output=True, text=True, **kwargs)


def psql(sql, **variables):
    args = ["docker", "exec", "-i", "-u", "postgres", DATABASE, "psql", "-X", "-q", "-At", "-v", "ON_ERROR_STOP=1", "-d", "pathsol"]
    for name, value in variables.items():
        args += ["-v", f"{name}={value}"]
    return run(args, input=sql).stdout.strip()


def token():
    with urlopen(Request(IMDS_TOKEN_URL, headers={"Metadata": "true"}), timeout=10) as response:
        return json.load(response)["access_token"]


def send(message):
    body = f"<QueueMessage><MessageText>{escape(json.dumps(message))}</MessageText></QueueMessage>".encode()
    request = Request(
        f"{QUEUE_URL}?messagettl=-1&visibilitytimeout=0",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token()}",
            "x-ms-version": X_MS_VERSION,
            "x-ms-date": email.utils.formatdate(usegmt=True),
            "Content-Type": "application/xml",
        },
    )
    with urlopen(request, timeout=30):
        pass


def job(slug, slide, version):
    job_id = str(uuid.uuid4())
    tenant, name, organ, material = psql(JOB_SQL, slug=slug, slide=slide, job=job_id, versao=version).split("|")
    message = {
        "job_id": job_id,
        "tenant_id": tenant,
        "slide_id": slide,
        "blob": f"wsi-{slug}/{name}",
        "organ": organ or None,
        "material": material,
        "pipeline_version": version,
        "attempt": 0,
    }
    try:
        send(message)
    except (urllib.error.URLError, OSError) as error:
        print(f"FALHA no envio do job {job_id}, que ficou QUEUED no banco sem mensagem: {error}", file=sys.stderr)
        return 1
    print(f"OK job {job_id} da lâmina {slide} no tenant {slug}: mensagem na fila")
    return 0


def parser():
    slug = checked(r"[a-z0-9]{2,20}", "tenant")
    parser = argparse.ArgumentParser(description="Produtor de jobs de teste da Fase 4 (decisão 7).")
    commands = parser.add_subparsers(dest="comando", required=True)
    tenant = commands.add_parser("tenant", help="cria o tenant, se não existir, e mostra o id")
    tenant.add_argument("slug", type=slug)
    slide = commands.add_parser("lamina", help="registra uma lâmina já enviada ao container do tenant")
    slide.add_argument("--tenant", required=True, type=slug)
    slide.add_argument("--arquivo", required=True, type=checked(rf"{UUID}\.[a-z0-9]{{2,5}}", "nome do blob (UUID.extensão)"))
    slide.add_argument("--sha256", required=True, type=checked(r"[0-9a-f]{64}", "sha256"))
    slide.add_argument("--material", required=True, choices=("biopsia", "peca", "citologia"))
    slide.add_argument("--coloracao", required=True, type=checked(r"[A-Z0-9_]{1,20}", "coloração"))
    slide.add_argument("--orgao", default="", type=checked(r"([a-z_]{2,40})?", "órgão"))
    new_job = commands.add_parser("job", help="cria um job para a lâmina e manda a mensagem à fila")
    new_job.add_argument("--tenant", required=True, type=slug)
    new_job.add_argument("--lamina", required=True, type=checked(UUID, "lâmina"))
    new_job.add_argument("--versao-pipeline", default="fase4-teste", type=checked(r"[A-Za-z0-9._-]{1,40}", "versão"))
    return parser


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.comando == "tenant":
            print(psql(TENANT_SQL, id=uuid.uuid4(), slug=args.slug))
            return 0
        if args.comando == "lamina":
            slide = args.arquivo.split(".")[0]
            psql(SLIDE_SQL, slug=args.tenant, slide=slide, nome=args.arquivo, sha256=args.sha256,
                 material=args.material, coloracao=args.coloracao, orgao=args.orgao)
            print(f"OK lâmina {slide} no tenant {args.tenant}")
            return 0
        return job(args.tenant, args.lamina, args.versao_pipeline)
    except subprocess.CalledProcessError as error:
        print(f"FALHA no banco: {error.stderr.strip()}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
