import json
import unittest
import uuid

from pathsol_worker import mensagem

JOB, TENANT, SLIDE = (str(uuid.uuid4()) for _ in range(3))


def text(**changes):
    body = {
        "job_id": JOB,
        "tenant_id": TENANT,
        "slide_id": SLIDE,
        "blob": f"wsi-publico/{SLIDE}.svs",
        "organ": "estomago",
        "material": "biopsia",
        "pipeline_version": "fase4-teste",
        "attempt": 0,
    }
    body.update(changes)
    return json.dumps({k: v for k, v in body.items() if v is not ...})


class Parse(unittest.TestCase):
    def test_valid_message(self):
        message = mensagem.parse(text())
        self.assertEqual(message.job_id, uuid.UUID(JOB))
        self.assertEqual((message.container, message.blob_name), ("wsi-publico", f"{SLIDE}.svs"))
        self.assertEqual((message.organ, message.material, message.attempt), ("estomago", "biopsia", 0))

    def test_organ_may_be_null(self):
        self.assertIsNone(mensagem.parse(text(organ=None)).organ)

    def test_round_trip_with_the_next_attempt(self):
        message = mensagem.parse(text())
        again = mensagem.parse(message.with_attempt(2).dumps())
        self.assertEqual(again.attempt, 2)
        self.assertEqual(again.job_id, message.job_id)

    def test_refuses_anything_off_the_contract(self):
        bad = {
            "not json": "{",
            "list": "[]",
            "missing field": text(attempt=...),
            "extra field": text(extra="x"),
            "bad uuid": text(job_id="123"),
            "blob of another slide": text(blob=f"wsi-publico/{uuid.uuid4()}.svs"),
            "blob outside a WSI container": text(blob=f"slide-h5/{SLIDE}.svs"),
            "original file name": text(blob="wsi-publico/caso-12345.svs"),
            "unknown material": text(material="congelacao"),
            "negative attempt": text(attempt=-1),
            "attempt as text": text(attempt="0"),
            "boolean attempt": text(attempt=True),
        }
        for case, raw in bad.items():
            with self.subTest(case), self.assertRaises(mensagem.InvalidMessage):
                mensagem.parse(raw)


if __name__ == "__main__":
    unittest.main()
