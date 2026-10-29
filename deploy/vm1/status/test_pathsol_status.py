import datetime
import unittest
import zoneinfo

import pathsol_status as status

BRASILIA = zoneinfo.ZoneInfo("America/Sao_Paulo")


def brasilia(month, day, hour, minute):
    return datetime.datetime(2026, month, day, hour, minute, tzinfo=BRASILIA)


class NextReturn(unittest.TestCase):
    def test_weeknight_shutdown_comes_back_next_morning(self):
        # Wednesday 28/10, 23:00: VM1 auto-shutdown.
        self.assertEqual(status.next_return(brasilia(10, 28, 23, 0)), brasilia(10, 29, 6, 15))

    def test_friday_shutdown_comes_back_on_monday(self):
        self.assertEqual(status.next_return(brasilia(10, 30, 23, 0)), brasilia(11, 2, 6, 15))

    def test_weekend_comes_back_on_monday(self):
        self.assertEqual(status.next_return(brasilia(10, 31, 10, 0)), brasilia(11, 2, 6, 15))
        self.assertEqual(status.next_return(brasilia(11, 1, 23, 59)), brasilia(11, 2, 6, 15))

    def test_before_six_fifteen_comes_back_the_same_day(self):
        self.assertEqual(status.next_return(brasilia(10, 29, 3, 0)), brasilia(10, 29, 6, 15))

    def test_at_six_fifteen_moves_to_the_next_weekday(self):
        self.assertEqual(status.next_return(brasilia(10, 29, 6, 15)), brasilia(10, 30, 6, 15))

    def test_utc_input(self):
        # 02:30 UTC on 29/10 is 23:30 on 28/10 in Brasilia.
        now = datetime.datetime(2026, 10, 29, 2, 30, tzinfo=datetime.timezone.utc)
        self.assertEqual(status.next_return(now), brasilia(10, 29, 6, 15))


class Document(unittest.TestCase):
    NOW = datetime.datetime(2026, 10, 29, 2, 30, tzinfo=datetime.timezone.utc)

    def test_up_has_no_return_time(self):
        self.assertEqual(status.document("up", self.NOW), {"status": "up", "updated_at": "2026-10-29T02:30:00+00:00"})

    def test_down_carries_the_return_time(self):
        self.assertEqual(
            status.document("down", self.NOW),
            {"status": "down", "updated_at": "2026-10-29T02:30:00+00:00", "back_at": "2026-10-29T06:15:00-03:00"},
        )


if __name__ == "__main__":
    unittest.main()
