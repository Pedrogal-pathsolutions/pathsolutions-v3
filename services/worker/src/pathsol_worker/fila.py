"""Azure Queue Storage over REST, with VM2's managed identity (plan, section 9.1).

On `jobs` the worker's role gets, deletes and updates messages; on the
dead-letter queue it only adds them. Every message is written with TTL -1:
Azure queues have no queue-level TTL, and the default 7 days would drop a job
that waits a week for VM2.
"""
import dataclasses
import email.utils
import urllib.parse
from urllib.request import Request, urlopen
from xml.etree import ElementTree
from xml.sax.saxutils import escape

from pathsol_worker import identidade

JOBS = "https://pathsolwsiv3.queue.core.windows.net/jobs"
DEAD_LETTER = "https://pathsoldlqv3.queue.core.windows.net/jobs-dead-letter"
X_MS_VERSION = "2024-11-04"


@dataclasses.dataclass(frozen=True)
class Received:
    id: str
    pop_receipt: str
    text: str
    dequeue_count: int


def _body(text):
    return f"<QueueMessage><MessageText>{escape(text)}</MessageText></QueueMessage>".encode()


class Queue:
    def __init__(self, url, opener=urlopen):
        self.url = url
        self.opener = opener
        self.token = identidade.Token(identidade.STORAGE, opener)

    def _call(self, method, path, query, data=None):
        request = Request(
            f"{self.url}/messages{path}?{urllib.parse.urlencode(query)}",
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token()}",
                "x-ms-version": X_MS_VERSION,
                "x-ms-date": email.utils.formatdate(usegmt=True),
                "Content-Type": "application/xml",
            },
        )
        with self.opener(request, timeout=30) as response:
            return response.read(), response.headers

    def get(self, visibility_timeout):
        """The next message, hidden for visibility_timeout seconds, or None."""
        body, _ = self._call("GET", "", {"numofmessages": 1, "visibilitytimeout": visibility_timeout})
        message = ElementTree.fromstring(body).find("QueueMessage")
        if message is None:
            return None
        return Received(message.findtext("MessageId"), message.findtext("PopReceipt"),
                        message.findtext("MessageText"), int(message.findtext("DequeueCount")))

    def delete(self, received):
        self._call("DELETE", f"/{received.id}", {"popreceipt": received.pop_receipt})

    def update(self, received, visibility_timeout, text):
        """Hides the message again and replaces its text in one call; returns it with the new pop receipt."""
        _, headers = self._call("PUT", f"/{received.id}",
                                {"popreceipt": received.pop_receipt, "visibilitytimeout": visibility_timeout}, _body(text))
        return dataclasses.replace(received, pop_receipt=headers["x-ms-popreceipt"], text=text)

    def put(self, text):
        self._call("POST", "", {"messagettl": -1}, _body(text))
