"""The job message of the queue (skill pathsol-contrato-h5, "Mensagem da fila").

Only internal identifiers, because the message stays readable in the
dead-letter queue. Anything off the contract is refused before any work; what
passes is still checked against the database (banco.JobStore.claim).
"""
import dataclasses
import json
import re
import uuid

FIELDS = {"job_id", "tenant_id", "slide_id", "blob", "organ", "material", "pipeline_version", "attempt"}
MATERIALS = ("biopsia", "peca", "citologia")
BLOB = re.compile(r"(wsi-[a-z0-9]{2,20})/([0-9a-f-]{36}\.[a-z0-9]{2,5})")


class InvalidMessage(Exception):
    pass


@dataclasses.dataclass(frozen=True)
class Message:
    job_id: uuid.UUID
    tenant_id: uuid.UUID
    slide_id: uuid.UUID
    container: str
    blob_name: str
    organ: str | None
    material: str
    pipeline_version: str
    attempt: int

    def with_attempt(self, attempt):
        return dataclasses.replace(self, attempt=attempt)

    def dumps(self):
        return json.dumps({
            "job_id": str(self.job_id),
            "tenant_id": str(self.tenant_id),
            "slide_id": str(self.slide_id),
            "blob": f"{self.container}/{self.blob_name}",
            "organ": self.organ,
            "material": self.material,
            "pipeline_version": self.pipeline_version,
            "attempt": self.attempt,
        })


def _text(value, pattern):
    return isinstance(value, str) and re.fullmatch(pattern, value) is not None


def parse(text):
    try:
        body = json.loads(text)
    except ValueError:
        raise InvalidMessage("a mensagem não é JSON") from None
    if not isinstance(body, dict) or set(body) != FIELDS:
        raise InvalidMessage("campos fora do contrato")
    try:
        job, tenant, slide = (uuid.UUID(body[key]) for key in ("job_id", "tenant_id", "slide_id"))
    except (ValueError, TypeError, AttributeError):
        raise InvalidMessage("identificador inválido") from None
    match = BLOB.fullmatch(body["blob"]) if isinstance(body["blob"], str) else None
    if match is None or not match.group(2).startswith(f"{slide}."):
        raise InvalidMessage("blob fora do contrato")
    if body["organ"] is not None and not _text(body["organ"], r"[a-z_]{2,40}"):
        raise InvalidMessage("órgão inválido")
    if body["material"] not in MATERIALS:
        raise InvalidMessage("material inválido")
    if not _text(body["pipeline_version"], r"[A-Za-z0-9._-]{1,40}"):
        raise InvalidMessage("versão inválida")
    if type(body["attempt"]) is not int or body["attempt"] < 0:
        raise InvalidMessage("tentativa inválida")
    return Message(job, tenant, slide, match.group(1), match.group(2), body["organ"], body["material"],
                   body["pipeline_version"], body["attempt"])
