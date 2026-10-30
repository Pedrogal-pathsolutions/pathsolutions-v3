"""Tokens of VM2's managed identity, from the IMDS (plan, section 8.3).

VM2 has only its user-assigned identity, so the IMDS answers without a client
id. A token is reused until five minutes before it expires.
"""
import json
import time
import urllib.parse
from urllib.request import Request

STORAGE = "https://storage.azure.com/"
IMDS = "http://169.254.169.254/metadata/identity/oauth2/token"
MARGIN = 300


class Token:
    def __init__(self, resource, opener):
        self.url = f"{IMDS}?{urllib.parse.urlencode({'api-version': '2018-02-01', 'resource': resource})}"
        self.opener = opener
        self.value, self.expires = None, 0

    def __call__(self):
        if time.time() > self.expires - MARGIN:
            with self.opener(Request(self.url, headers={"Metadata": "true"}), timeout=10) as response:
                answer = json.load(response)
            self.value, self.expires = answer["access_token"], int(answer["expires_on"])
        return self.value
