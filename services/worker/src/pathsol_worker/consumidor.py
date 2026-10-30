"""One delivery of the jobs queue, from the message to the job's final state (plan, section 9.1).

process(job) returns the outcome (COMPLETED, QC_FAILED or UNSUPPORTED_FORMAT)
or raises: anything raised is a technical failure, counted in the database.
Only those go back to the queue, hidden with backoff; the third goes to the
dead-letter queue, only then leaves the main queue, and the job becomes
DEAD_LETTER. A message that leaves the main queue was always handled first:
written to the database or to the dead-letter queue.
"""
import dataclasses

from pathsol_worker import banco, mensagem

BACKOFF = 60


@dataclasses.dataclass(frozen=True)
class Completed:
    h5_blob: str
    h5_size: int
    h5_sha256: str
    extractor_version: str
    state = "COMPLETED"

    def record(self, store, job):
        store.complete(job, self.h5_blob, self.h5_size, self.h5_sha256, self.extractor_version)


@dataclasses.dataclass(frozen=True)
class QcFailed:
    reason: str
    scores_blob: str | None = None
    state = "QC_FAILED"

    def record(self, store, job):
        store.qc_failed(job, self.reason, self.scores_blob)


@dataclasses.dataclass(frozen=True)
class Unsupported:
    reason: str
    state = "UNSUPPORTED_FORMAT"

    def record(self, store, job):
        store.unsupported(job, self.reason)


def handle(received, jobs, dead_letter, store, process):
    """Returns what happened, for the log. A database error is raised and leaves the message for the visibility timeout."""
    try:
        message = mensagem.parse(received.text)
    except mensagem.InvalidMessage:
        dead_letter.put(received.text)
        jobs.delete(received)
        return "inválida"
    job = store.claim(message)
    if job is None:
        dead_letter.put(received.text)
        jobs.delete(received)
        return "não confere com o banco"
    if job.status != "RUNNING":
        jobs.delete(received)
        return "já terminado"
    try:
        outcome = process(job)
    except Exception:  # every failure of the processing is a technical one
        attempt = store.failed(job)
        text = message.with_attempt(attempt).dumps()
        if attempt >= banco.MAX_ATTEMPTS:
            dead_letter.put(text)
            jobs.delete(received)
            store.dead_letter(job)
            return "DEAD_LETTER"
        jobs.update(received, BACKOFF * 2 ** (attempt - 1), text)
        return "nova tentativa"
    outcome.record(store, job)
    jobs.delete(received)
    return outcome.state
