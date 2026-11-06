import json
import unittest
import uuid

from pathsol_worker import banco, consumidor, fila
from pathsol_worker.mensagem import Message

SLIDE = uuid.uuid4()
MESSAGE = Message(uuid.uuid4(), uuid.uuid4(), SLIDE, "wsi-publico", f"{SLIDE}.svs", "estomago", "biopsia", "teste", 0)
TEXT = MESSAGE.dumps()
THIRD_TRY = MESSAGE.with_attempt(2).dumps()


def boom(job):
    raise RuntimeError("falha técnica")


class Log(list):
    """One list for every call, to check the order across queue and database."""


class FakeQueue:
    def __init__(self, name, log):
        self.name, self.log = name, log

    def delete(self, received):
        self.log.append((self.name, "delete", received.id))

    def update(self, received, visibility_timeout, text):
        self.text = text
        self.log.append((self.name, "update", visibility_timeout, json.loads(text)["attempt"]))

    def put(self, text):
        self.log.append((self.name, "put", text))


class FakeStore:
    """The calls named in `down` find the database down."""

    def __init__(self, log, job="running", attempt=1, down=()):
        self.log, self.job, self.attempt, self.down = log, job, attempt, down

    def call(self, name, *args):
        self.log.append(("banco", name, *args))
        if name in self.down:
            raise banco.Unavailable("banco fora do ar")

    def claim(self, message):
        self.call("claim")
        if self.job is None:
            return None
        status = "RUNNING" if self.job == "running" else "COMPLETED"
        return banco.Job(message.job_id, message.tenant_id, message.slide_id, message.container, message.blob_name,
                         "0" * 64, message.organ, message.material, "HE", status, 0)

    def __getattr__(self, name):
        if name in ("complete", "qc_failed", "unsupported", "dead_letter"):
            return lambda job, *args: self.call(name, *args)
        raise AttributeError(name)

    def failed(self, job):
        self.call("failed")
        return self.attempt


def handle(text=TEXT, store_job="running", attempt=1, process=None, down=()):
    log = Log()
    received = fila.Received("m1", "pop", text, 1)
    jobs, dead = FakeQueue("jobs", log), FakeQueue("dlq", log)
    result = consumidor.handle(received, jobs, dead, FakeStore(log, store_job, attempt, down), process or (lambda job: None))
    return result, log


class Handle(unittest.TestCase):
    def test_invalid_message_goes_to_the_dead_letter_queue_first(self):
        result, log = handle(text="{not json")
        self.assertEqual(result, "inválida")
        self.assertEqual(log, [("dlq", "put", "{not json"), ("jobs", "delete", "m1")])

    def test_message_that_does_not_match_the_database_is_not_processed(self):
        called = []
        result, log = handle(store_job=None, process=called.append)
        self.assertEqual(result, "não confere com o banco")
        self.assertEqual(log, [("banco", "claim"), ("dlq", "put", TEXT), ("jobs", "delete", "m1")])
        self.assertEqual(called, [])

    def test_finished_job_only_leaves_the_queue(self):
        called = []
        result, log = handle(store_job="done", process=called.append)
        self.assertEqual(result, "já terminado")
        self.assertEqual(log, [("banco", "claim"), ("jobs", "delete", "m1")])
        self.assertEqual(called, [])

    def test_outcome_is_written_before_the_message_leaves(self):
        outcomes = (
            (consumidor.Completed("t/s/h/j.h5", 10, "a" * 64, "v1"), ("banco", "complete", "t/s/h/j.h5", 10, "a" * 64, "v1"), "COMPLETED"),
            (consumidor.QcFailed("focus", "t/s/h/j.qc.h5"), ("banco", "qc_failed", "focus", "t/s/h/j.qc.h5"), "QC_FAILED"),
            (consumidor.QcFailed("empty_glass"), ("banco", "qc_failed", "empty_glass", None), "QC_FAILED"),
            (consumidor.Unsupported("scale_unavailable"), ("banco", "unsupported", "scale_unavailable"), "UNSUPPORTED_FORMAT"),
        )
        for outcome, write, state in outcomes:
            with self.subTest(state=state, write=write):
                result, log = handle(process=lambda job, o=outcome: o)
                self.assertEqual(result, state)
                self.assertEqual(log, [("banco", "claim"), write, ("jobs", "delete", "m1")])

    def test_technical_failure_returns_with_backoff_and_the_next_attempt(self):
        for attempt, wait in ((1, 60), (2, 120)):
            with self.subTest(attempt=attempt):
                result, log = handle(attempt=attempt, process=boom)
                self.assertEqual(result, "nova tentativa")
                self.assertEqual(log, [("banco", "claim"), ("banco", "failed"), ("jobs", "update", wait, attempt)])

    def test_third_failure_goes_to_the_dead_letter_queue_then_leaves_then_is_recorded(self):
        result, log = handle(attempt=banco.MAX_ATTEMPTS, process=boom)
        self.assertEqual(result, "DEAD_LETTER")
        self.assertEqual([entry[:2] for entry in log],
                         [("banco", "claim"), ("banco", "failed"), ("dlq", "put"), ("jobs", "delete"), ("banco", "dead_letter")])
        self.assertEqual(json.loads(log[2][2])["attempt"], banco.MAX_ATTEMPTS)

    def test_database_down_puts_the_message_back_with_its_own_attempt(self):
        completed = consumidor.Completed("t/s/h/j.h5", 10, "a" * 64, "v1")
        cases = (
            ("claim", boom, [("banco", "claim")]),
            ("failed", boom, [("banco", "claim"), ("banco", "failed")]),
            ("complete", lambda job: completed, [("banco", "claim"), ("banco", "complete", "t/s/h/j.h5", 10, "a" * 64, "v1")]),
        )
        for down, process, calls in cases:
            with self.subTest(down=down):
                # A message on its third try: one more count would send it to the dead-letter queue.
                result, log = handle(text=THIRD_TRY, attempt=banco.MAX_ATTEMPTS, process=process, down=(down,))
                self.assertEqual(result, "banco indisponível")
                self.assertEqual(log, [*calls, ("jobs", "update", 60, 2)])

    def test_five_deliveries_with_the_database_down_never_reach_the_dead_letter_queue(self):
        log = Log()
        jobs, dead = FakeQueue("jobs", log), FakeQueue("dlq", log)
        store = FakeStore(log, attempt=banco.MAX_ATTEMPTS, down=("claim",))
        text = THIRD_TRY
        for delivery in range(5):
            consumidor.handle(fila.Received(f"m{delivery}", "pop", text, delivery + 1), jobs, dead, store, boom)
            text = jobs.text
        self.assertEqual(log, [("banco", "claim"), ("jobs", "update", 60, 2)] * 5)

    def test_an_outage_after_the_message_left_the_queue_is_raised(self):
        log = Log()
        store = FakeStore(log, attempt=banco.MAX_ATTEMPTS, down=("dead_letter",))
        with self.assertRaises(banco.Unavailable):
            consumidor.handle(fila.Received("m1", "pop", TEXT, 1), FakeQueue("jobs", log), FakeQueue("dlq", log), store, boom)
        self.assertEqual([entry[:2] for entry in log],
                         [("banco", "claim"), ("banco", "failed"), ("dlq", "put"), ("jobs", "delete"), ("banco", "dead_letter")])

    def test_another_database_error_leaves_the_message_for_the_visibility_timeout(self):
        class Refused(FakeStore):
            def claim(self, message):
                raise banco.psycopg.errors.InsufficientPrivilege("permissão negada")

        log = Log()
        with self.assertRaises(banco.psycopg.errors.InsufficientPrivilege):
            consumidor.handle(fila.Received("m1", "pop", TEXT, 1), FakeQueue("jobs", log), FakeQueue("dlq", log), Refused(log), None)
        self.assertEqual(log, [])


if __name__ == "__main__":
    unittest.main()
