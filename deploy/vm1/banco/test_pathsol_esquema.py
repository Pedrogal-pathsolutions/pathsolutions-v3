import subprocess
import unittest
from unittest import mock

import pathsol_esquema as esquema

IMAGE = "pathsol-api:abc1234"


def done(stdout="", returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


class Fake:
    """Answers the docker calls in order and keeps them."""

    def __init__(self, *answers):
        self.answers = list(answers)
        self.calls = []

    def __call__(self, args, **kwargs):
        self.calls.append((args, kwargs.get("input")))
        return self.answers.pop(0)


class Apply(unittest.TestCase):
    def run_with(self, fake):
        with mock.patch.object(esquema, "run", fake):
            return esquema.apply(IMAGE)

    def test_empty_database_gets_roles_then_every_migration(self):
        fake = Fake(done("-- papeis"), done(), done("f\n"), done("-- tudo"), done(), done("t\n"), done("0001\n"))
        self.assertEqual(self.run_with(fake), (None, "0001"))
        (roles_args, _), (psql_roles, roles_sql), _, (migration_args, _), (psql_migration, migration_sql), _, _ = fake.calls
        self.assertEqual(roles_args, ["docker", "run", "--rm", "--network", "none", IMAGE, "python", "-m", "pathsol_api.esquema", "papeis"])
        self.assertEqual(psql_roles[:6], ["docker", "exec", "-i", "-u", "postgres", "pathsol-banco"])
        self.assertIn("ON_ERROR_STOP=1", psql_roles)
        self.assertEqual(psql_roles[-1], "postgres")
        self.assertEqual(roles_sql, "-- papeis")
        self.assertEqual(migration_args[-1], "migracao")
        self.assertEqual(psql_migration[-1], "pathsol")
        self.assertEqual(migration_sql, "-- tudo")

    def test_migrates_from_the_current_revision(self):
        fake = Fake(done("-- papeis"), done(), done("t\n"), done("0001\n"), done("-- 0002"), done(), done("t\n"), done("0002\n"))
        self.assertEqual(self.run_with(fake), ("0001", "0002"))
        self.assertEqual(fake.calls[4][0][-3:], ["migracao", "--de", "0001"])

    def test_refuses_an_image_name_that_could_be_an_option(self):
        with self.assertRaises(SystemExit):
            esquema.main(["--privileged"])


if __name__ == "__main__":
    unittest.main()
