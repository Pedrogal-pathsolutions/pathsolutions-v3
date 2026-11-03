"""VM2's power, as the worker sees it (plan, section 7 and section 8.3, layer 1).

When the queue stays idle, the worker deallocates VM2 through ARM with its own
identity, never from the OS: a VM stopped from inside keeps billing. A valid
maintenance marker on the host keeps VM2 on (pattern 11): one line with a UTC
deadline, at most 4 h after the file was written. The worker also takes no new
job when the worst measured time would pass VM1's next shutdown, because the
database lives on VM1.
"""
import datetime
import os
from urllib.request import Request, urlopen

from pathsol_worker import identidade

ARM = "https://management.azure.com/"
VM2 = ("/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1/resourceGroups/rg-prod-brsouth-001"
       "/providers/Microsoft.Compute/virtualMachines/vm-appfoundation-prod-001")
DEALLOCATE_URL = f"https://management.azure.com{VM2}/deallocate?api-version=2025-04-01"
MAX_TERM = datetime.timedelta(hours=4)


def maintenance_until(path, now):
    """The marker's deadline while it holds; None without a marker; ValueError for any other marker."""
    try:
        with open(path) as f:
            text = f.read().strip()
        written = datetime.datetime.fromtimestamp(os.stat(path).st_mtime, datetime.UTC)
    except FileNotFoundError:
        return None
    deadline = datetime.datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.UTC)
    if not now < deadline <= written + MAX_TERM:
        raise ValueError(f"marcador de manutenção fora do prazo: {text}")
    return deadline


def deallocate(opener=urlopen):
    token = identidade.Token(ARM, opener)
    request = Request(DEALLOCATE_URL, data=b"", method="POST", headers={"Authorization": f"Bearer {token()}"})
    with opener(request, timeout=30) as response:
        return response.status


def accepting(now, worst, shutdown):
    """False when a job taken now, lasting the worst measured time, could pass VM1's next shutdown."""
    next_shutdown = datetime.datetime.combine(now.date(), shutdown, datetime.UTC)
    if next_shutdown <= now:
        next_shutdown += datetime.timedelta(days=1)
    return now + datetime.timedelta(seconds=worst) < next_shutdown
