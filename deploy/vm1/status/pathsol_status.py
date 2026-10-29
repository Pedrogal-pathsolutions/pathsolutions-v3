#!/usr/bin/python3
"""Writes status.json to the status account's static website (plan, section 18).

"up" when VM1 boots; "down" when it shuts down, with VM1 back at 06:15
(Brasilia) on the next weekday, after the TurnOn-VMs runbook starts it at
06:00. Maintenance notices are published by hand, with the same fields.
Signs in with VM1's system identity, which may write only in $web.
"""
import datetime
import email.utils
import json
import sys
import time
import urllib.request
import zoneinfo

BLOB_URL = "https://pathsolstatusv3.blob.core.windows.net/$web/status.json"
IMDS_TOKEN_URL = (
    "http://169.254.169.254/metadata/identity/oauth2/token"
    "?api-version=2018-02-01&resource=https://storage.azure.com/"
)
BRASILIA = zoneinfo.ZoneInfo("America/Sao_Paulo")
BACK_AT = datetime.time(6, 15)


def next_return(now):
    """06:15 in Brasilia on the next weekday, or today if it is still earlier."""
    local = now.astimezone(BRASILIA)
    day = local.date()
    if local.time() >= BACK_AT:
        day += datetime.timedelta(days=1)
    while day.weekday() >= 5:
        day += datetime.timedelta(days=1)
    return datetime.datetime.combine(day, BACK_AT, tzinfo=BRASILIA)


def document(state, now):
    doc = {"status": state, "updated_at": now.astimezone(datetime.timezone.utc).isoformat(timespec="seconds")}
    if state == "down":
        doc["back_at"] = next_return(now).isoformat()
    return doc


def put_status(doc):
    token_request = urllib.request.Request(IMDS_TOKEN_URL, headers={"Metadata": "true"})
    with urllib.request.urlopen(token_request, timeout=10) as response:
        token = json.load(response)["access_token"]
    # The extension polls at most once a minute and must never see a stale state.
    request = urllib.request.Request(
        BLOB_URL,
        data=json.dumps(doc).encode(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {token}",
            "x-ms-version": "2024-11-04",
            "x-ms-date": email.utils.formatdate(usegmt=True),
            "x-ms-blob-type": "BlockBlob",
            "x-ms-blob-content-type": "application/json",
            "x-ms-blob-cache-control": "no-cache",
        },
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status


def main(argv):
    if len(argv) != 2 or argv[1] not in ("up", "down"):
        sys.exit("usage: pathsol-status up|down")
    doc = document(argv[1], datetime.datetime.now(datetime.timezone.utc))
    # At boot the network or IMDS may still be coming up.
    for pause in (2, 5, None):
        try:
            print(f"status.json {doc['status']}: HTTP {put_status(doc)}")
            return
        except OSError as error:  # urllib raises URLError and HTTPError, both OSError
            print(f"status.json {doc['status']}: {error}", file=sys.stderr)
            if pause:
                time.sleep(pause)
    sys.exit(1)


if __name__ == "__main__":
    main(sys.argv)
