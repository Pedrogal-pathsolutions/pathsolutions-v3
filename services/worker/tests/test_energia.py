import datetime
import io
import json
import os
import tempfile
import unittest

from pathsol_worker import energia

UTC = datetime.UTC
WRITTEN = datetime.datetime(2026, 11, 3, 12, 0, tzinfo=UTC)


class Response(io.BytesIO):
    status = 202


class Arm:
    def __init__(self):
        self.requests = []

    def __call__(self, request, timeout=None):
        self.requests.append(request)
        if request.full_url.startswith("http://169.254.169.254/"):
            return Response(json.dumps({"access_token": "tok", "expires_on": "9999999999"}).encode())
        return Response(b"")


class Marker(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.dir.name, "manutencao")

    def tearDown(self):
        self.dir.cleanup()

    def write(self, text):
        with open(self.path, "w") as f:
            f.write(text)
        os.utime(self.path, (WRITTEN.timestamp(), WRITTEN.timestamp()))

    def test_no_marker_is_no_maintenance(self):
        self.assertIsNone(energia.maintenance_until(self.path, WRITTEN))

    def test_a_deadline_within_four_hours_of_writing_holds_until_it_passes(self):
        self.write("2026-11-03T16:00:00Z\n")
        deadline = datetime.datetime(2026, 11, 3, 16, 0, tzinfo=UTC)
        self.assertEqual(energia.maintenance_until(self.path, WRITTEN + datetime.timedelta(hours=3)), deadline)
        with self.assertRaisesRegex(ValueError, "fora do prazo"):
            energia.maintenance_until(self.path, deadline)

    def test_a_deadline_beyond_the_maximum_term_is_refused(self):
        self.write("2026-11-03T16:00:01Z")
        with self.assertRaisesRegex(ValueError, "fora do prazo"):
            energia.maintenance_until(self.path, WRITTEN)

    def test_a_malformed_marker_is_refused(self):
        self.write("amanhã")
        with self.assertRaises(ValueError):
            energia.maintenance_until(self.path, WRITTEN)


class Deallocate(unittest.TestCase):
    def test_posts_deallocate_on_vm2_with_a_management_token(self):
        arm = Arm()
        self.assertEqual(energia.deallocate(arm), 202)
        token, call = arm.requests
        self.assertIn("resource=https%3A%2F%2Fmanagement.azure.com%2F", token.full_url)
        self.assertEqual(call.get_method(), "POST")
        self.assertEqual(call.full_url, "https://management.azure.com/subscriptions/bd87a1ca-e4f5-460b-9f12-c89e114293f1"
                         "/resourceGroups/rg-prod-brsouth-001/providers/Microsoft.Compute/virtualMachines"
                         "/vm-appfoundation-prod-001/deallocate?api-version=2025-04-01")
        self.assertEqual(call.get_header("Authorization"), "Bearer tok")


class Schedule(unittest.TestCase):
    def test_no_new_job_when_the_worst_time_passes_the_next_vm1_shutdown(self):
        shutdown = datetime.time(2, 0)
        evening = datetime.datetime(2026, 11, 3, 1, 44, tzinfo=UTC)
        self.assertTrue(energia.accepting(evening, 900, shutdown))
        self.assertFalse(energia.accepting(evening + datetime.timedelta(minutes=1), 900, shutdown))
        self.assertTrue(energia.accepting(datetime.datetime(2026, 11, 3, 2, 0, tzinfo=UTC), 900, shutdown))


if __name__ == "__main__":
    unittest.main()
