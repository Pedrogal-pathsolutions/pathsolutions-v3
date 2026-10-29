import base64
import io
import json
import unittest

import pathsol_banco as banco

DAY = 86400
HOUR = 3600
NOW = 1_793_000_000.0


class BackupType(unittest.TestCase):
    def test_no_full_backup_yet(self):
        self.assertEqual(banco.backup_type(None, NOW), "full")

    def test_full_six_days_old_or_more(self):
        # Monday's 06:00 run starts a few seconds earlier than the last one.
        self.assertEqual(banco.backup_type(NOW - 7 * DAY + 30, NOW), "full")
        self.assertEqual(banco.backup_type(NOW - 6 * DAY, NOW), "full")

    def test_differential_inside_the_week(self):
        self.assertEqual(banco.backup_type(NOW - DAY, NOW), "diff")
        self.assertEqual(banco.backup_type(NOW - 6 * DAY + 60, NOW), "diff")


class AgeCheck(unittest.TestCase):
    def check(self, last, uptime):
        return banco.age_check("backup", last, NOW, uptime, max_age=26 * HOUR, grace=3 * HOUR)

    def test_recent(self):
        ok, message = self.check(NOW - 2 * HOUR, uptime=10 * HOUR)
        self.assertTrue(ok)
        self.assertIn("2,0 h", message)

    def test_old_after_the_boot_window(self):
        ok, _ = self.check(NOW - 27 * HOUR, uptime=4 * HOUR)
        self.assertFalse(ok)

    def test_old_right_after_boot_waits_for_the_daily_run(self):
        # Monday morning: the last backup is Friday's.
        ok, message = self.check(NOW - 72 * HOUR, uptime=HOUR)
        self.assertTrue(ok)
        self.assertIn("partida", message)

    def test_none_ever_is_a_failure_even_after_boot(self):
        ok, _ = self.check(None, uptime=HOUR)
        self.assertFalse(ok)


class CertCheck(unittest.TestCase):
    def test_ninety_day_certificate_uses_21_days(self):
        not_before = NOW - 60 * DAY
        not_after = NOW + 30 * DAY
        self.assertTrue(banco.cert_check("certificado-app", not_before, not_after, NOW)[0])
        self.assertTrue(banco.cert_check("certificado-app", not_before, not_after, not_after - 21 * DAY)[0])
        self.assertFalse(banco.cert_check("certificado-app", not_before, not_after, not_after - 21 * DAY + 1)[0])

    def test_short_certificate_uses_a_quarter_of_its_life(self):
        # 64 days, renewed at about 2/3 of its life: 21 days left is normal.
        not_before = NOW - 43 * DAY
        not_after = NOW + 21 * DAY
        self.assertTrue(banco.cert_check("certificado-app", not_before, not_after, NOW)[0])
        self.assertTrue(banco.cert_check("certificado-app", not_before, not_after, not_after - 16 * DAY)[0])
        self.assertFalse(banco.cert_check("certificado-app", not_before, not_after, not_after - 15 * DAY)[0])

    def test_expired(self):
        ok, message = banco.cert_check("certificado-banco", NOW - 400 * DAY, NOW - DAY, NOW)
        self.assertFalse(ok)
        self.assertIn("certificado-banco", message)


class ArchiveCheck(unittest.TestCase):
    def test_nothing_waiting(self):
        self.assertTrue(banco.archive_check(None, NOW)[0])

    def test_segment_waiting_briefly(self):
        self.assertTrue(banco.archive_check(NOW - 9 * 60, NOW)[0])

    def test_segment_stuck(self):
        self.assertFalse(banco.archive_check(NOW - 11 * 60, NOW)[0])


class WalDropped(unittest.TestCase):
    def test_archived_and_in_the_repository(self):
        self.assertFalse(banco.wal_dropped("000000010000000000000007", "000000010000000000000007"))

    def test_marked_archived_but_missing_from_the_repository(self):
        self.assertTrue(banco.wal_dropped("000000010000000000000009", "000000010000000000000007"))

    def test_backup_label_and_history_files_are_not_segments(self):
        # A .backup file can be archived just before its segment.
        self.assertFalse(banco.wal_dropped("000000010000000000000008.00000028.backup", "000000010000000000000007"))
        self.assertFalse(banco.wal_dropped("00000002.history", "000000010000000000000007"))

    def test_unknown_values(self):
        self.assertFalse(banco.wal_dropped(None, "000000010000000000000007"))
        self.assertFalse(banco.wal_dropped("000000010000000000000007", None))


class Blocks(unittest.TestCase):
    def test_splits_a_stream_into_fixed_blocks(self):
        chunks = list(banco.blocks(io.BytesIO(b"abcdefghij"), 4))
        self.assertEqual(chunks, [b"abcd", b"efgh", b"ij"])

    def test_empty_stream_makes_no_block(self):
        self.assertEqual(list(banco.blocks(io.BytesIO(b""), 4)), [])

    def test_block_ids_have_one_length(self):
        ids = [banco.block_id(i) for i in (0, 9, 49999)]
        self.assertEqual(len({len(i) for i in ids}), 1)
        self.assertEqual(base64.b64decode(ids[1]), b"000009")


class NewestDumpRun(unittest.TestCase):
    def test_newest_complete_run(self):
        names = [
            "dump/20261028T090101Z/canario.dump",
            "dump/20261028T090101Z/completo",
            "dump/20261029T090200Z/canario.dump",
            "dump/20261029T090200Z/completo",
            "dump/20261029T120000Z/globais.sql",  # unfinished: no marker
        ]
        self.assertEqual(banco.newest_dump_run(names), "20261029T090200Z")

    def test_none_complete(self):
        self.assertIsNone(banco.newest_dump_run(["dump/20261029T120000Z/globais.sql"]))

    def test_run_time(self):
        self.assertEqual(banco.run_time("20261029T090200Z"), 1_793_264_520.0)


class ParseInfo(unittest.TestCase):
    INFO = [{
        "name": "pathsol",
        "status": {"code": 0, "message": "ok"},
        "archive": [{"id": "18-1", "max": "000000010000000000000009", "min": "000000010000000000000001"}],
        "backup": [
            {"type": "full", "timestamp": {"start": 100, "stop": 160}, "info": {"size": 30_000_000}, "error": False},
            {"type": "diff", "timestamp": {"start": 200, "stop": 230}, "info": {"size": 31_000_000}, "error": False},
        ],
    }]

    def test_fields(self):
        info = banco.parse_info(json.dumps(self.INFO))
        self.assertEqual(info["status"], (0, "ok"))
        self.assertEqual(info["last_full_stop"], 160)
        self.assertEqual(info["last_stop"], 230)
        self.assertEqual(info["last_error"], False)
        self.assertEqual(info["size"], 31_000_000)
        self.assertEqual(info["archive_max"], "000000010000000000000009")

    def test_new_stanza_without_backups(self):
        info = banco.parse_info(json.dumps([{"name": "pathsol", "status": {"code": 2, "message": "no valid backups"}, "archive": [], "backup": []}]))
        self.assertEqual(info["status"], (2, "no valid backups"))
        self.assertIsNone(info["last_full_stop"])
        self.assertIsNone(info["last_stop"])
        self.assertIsNone(info["archive_max"])


class GlobalsErrors(unittest.TestCase):
    def test_existing_superuser_is_expected(self):
        self.assertTrue(banco.globals_errors_ok('psql:/r/globais.sql:14: ERROR:  role "postgres" already exists\n'))

    def test_any_other_error_fails(self):
        stderr = 'psql:/r/globais.sql:14: ERROR:  role "postgres" already exists\npsql:/r/globais.sql:20: ERROR:  syntax error\n'
        self.assertFalse(banco.globals_errors_ok(stderr))


if __name__ == "__main__":
    unittest.main()
