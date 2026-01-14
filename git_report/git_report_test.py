import unittest
from datetime import datetime
from pathlib import Path

import git_report


class GitReportTest(unittest.TestCase):
    def test_format_period(self):
        date: datetime = datetime(1990, 2, 1)
        self.assertEqual(
            "1990-02-01",
            git_report.format_period(date=date, period=git_report.Period.DAY),
        )
        self.assertEqual(
            "1990-W05",
            git_report.format_period(date=date, period=git_report.Period.WEEK),
        )
        self.assertEqual(
            "1990-02",
            git_report.format_period(date=date, period=git_report.Period.MONTH),
        )

    def test_format_period_error(self):
        with self.assertRaises(ValueError):
            git_report.format_period(date=datetime(1990, 1, 1), period=None)

        with self.assertRaises(ValueError):
            git_report.format_period(date=None, period=git_report.Period.DAY)

    def test_git_stats_error(self):
        with self.assertRaises(RuntimeError):
            git_report.get_commit_stats(Path("/"), None, None, None)


if __name__ == "__main__":
    unittest.main()
