import io
import json
import unittest
import urllib.parse

from pathsol_worker import fila

URL = "https://pathsolwsiv3.queue.core.windows.net/jobs"
LISTING = b"""<?xml version="1.0" encoding="utf-8"?>
<QueueMessagesList><QueueMessage><MessageId>m-1</MessageId><InsertionTime>x</InsertionTime>
<ExpirationTime>x</ExpirationTime><PopReceipt>AgAAA+/==</PopReceipt><TimeNextVisible>x</TimeNextVisible>
<DequeueCount>2</DequeueCount><MessageText>{"a": "&lt;b&gt;"}</MessageText></QueueMessage></QueueMessagesList>"""


class Response(io.BytesIO):
    def __init__(self, body=b"", headers=None):
        super().__init__(body)
        self.headers = headers or {}


class Opener:
    def __init__(self, *bodies):
        self.bodies = list(bodies)
        self.requests = []

    def __call__(self, request, timeout=None):
        if request.full_url.startswith("http://169.254.169.254/"):
            self.requests.append(("imds", request))
            return Response(json.dumps({"access_token": "tok", "expires_on": "9999999999"}).encode())
        self.requests.append(("fila", request))
        return self.bodies.pop(0)

    def calls(self):
        return [r for kind, r in self.requests if kind == "fila"]


class Queue(unittest.TestCase):
    def test_get_parses_one_message_with_the_visibility_timeout(self):
        opener = Opener(Response(LISTING))
        received = fila.Queue(URL, opener).get(1800)
        self.assertEqual(received, fila.Received("m-1", "AgAAA+/==", '{"a": "<b>"}', 2))
        request = opener.calls()[0]
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(request.full_url).query)
        self.assertEqual((request.get_method(), query["numofmessages"], query["visibilitytimeout"]), ("GET", ["1"], ["1800"]))
        self.assertEqual(request.get_header("Authorization"), "Bearer tok")
        self.assertIsNotNone(request.get_header("X-ms-version"))

    def test_empty_queue(self):
        empty = b'<?xml version="1.0" encoding="utf-8"?><QueueMessagesList />'
        self.assertIsNone(fila.Queue(URL, Opener(Response(empty))).get(60))

    def test_delete_and_update_carry_the_pop_receipt(self):
        opener = Opener(Response(), Response(headers={"x-ms-popreceipt": "novo"}))
        queue = fila.Queue(URL, opener)
        received = fila.Received("m-1", "AgAAA+/==", "{}", 1)
        queue.delete(received)
        updated = queue.update(received, 120, '{"attempt": 1}')
        delete, update = opener.calls()
        self.assertEqual(delete.get_method(), "DELETE")
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(delete.full_url).query)["popreceipt"], ["AgAAA+/=="])
        self.assertTrue(delete.full_url.startswith(f"{URL}/messages/m-1?"))
        self.assertEqual(update.get_method(), "PUT")
        self.assertEqual(urllib.parse.parse_qs(urllib.parse.urlsplit(update.full_url).query)["visibilitytimeout"], ["120"])
        self.assertIn(b'<MessageText>{"attempt": 1}</MessageText>', update.data)
        self.assertEqual(updated, fila.Received("m-1", "novo", '{"attempt": 1}', 1))

    def test_put_never_expires(self):
        opener = Opener(Response())
        fila.Queue(URL, opener).put('{"a": "<b>"}')
        request = opener.calls()[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertIn("messagettl=-1", request.full_url)
        self.assertIn(b"&lt;b&gt;", request.data)

    def test_token_is_asked_once(self):
        opener = Opener(Response(), Response())
        queue = fila.Queue(URL, opener)
        queue.put("{}")
        queue.put("{}")
        self.assertEqual(sum(1 for kind, _ in opener.requests if kind == "imds"), 1)


if __name__ == "__main__":
    unittest.main()
