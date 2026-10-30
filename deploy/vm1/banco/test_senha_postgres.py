"""The SCRAM verifier against PostgreSQL 18's own, for the same salt.

Runs in the API test image, which has PostgreSQL 18:

    docker run --rm --network none -v "$PWD/deploy/vm1/banco:/banco:ro" \
        -e PYTHONPATH=/banco:/src/services/api/tests pathsol-api-teste:<tag> \
        python -m unittest discover -s /banco -p 'test_senha_postgres.py'
"""
import base64
import unittest

import pathsol_senha_worker as senha

try:
    from cluster import Cluster
except ImportError:
    raise unittest.SkipTest("roda na imagem de teste da API") from None


class SameAsPostgres(unittest.TestCase):
    def test_verifier_matches_the_one_postgres_computes(self):
        cluster = Cluster()
        self.addCleanup(cluster.stop)
        cluster.psql("create role conferencia login; set password_encryption = 'scram-sha-256'; "
                     "alter role conferencia password 'senha com espaço e ç'")
        out = cluster.psql("\\pset format unaligned\n\\pset tuples_only on\n"
                           "select rolpassword from pg_authid where rolname = 'conferencia'")
        stored = out.strip().splitlines()[-1]
        iterations, salt = stored.split("$")[1].split(":")
        mine = senha.scram_verifier("senha com espaço e ç", base64.b64decode(salt), int(iterations))
        self.assertEqual(mine, stored)


if __name__ == "__main__":
    unittest.main()
