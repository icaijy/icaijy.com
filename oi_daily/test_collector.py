"""Network-free regression tests for OI daily snapshots."""
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from oi_daily import collector as c


class FakeSession:
    pass


class CountsTest(unittest.TestCase):
    def test_codeforces_pagination_and_dedup(self):
        row = lambda idx, cid, verdict: {
            "verdict": verdict, "problem": {"contestId": cid, "index": idx}}
        pages = [
            {"status": "OK", "result": [row("A", 100, "OK"), row("A", 100, "WRONG_ANSWER")]},
            {"status": "OK", "result": [row("A", 100, "OK"), row("B", 200, "OK")]},
            {"status": "OK", "result": [row("C", 300, "WRONG_ANSWER")]},
        ]
        with patch.object(c, "CF_PAGE_SIZE", 2), patch.object(c, "get_json", side_effect=pages) as fetch, patch.object(c.time, "sleep"):
            self.assertEqual(c.codeforces_count(FakeSession()), 2)
            self.assertEqual(fetch.call_count, 3)

    def test_atcoder_paginated_boundary_and_repeated_ac(self):
        row = lambda sid, second, pid: {
            "id": sid, "epoch_second": second, "problem_id": pid, "result": "AC"}
        pages = [
            [row(1, 10, "abc_a"), row(2, 11, "abc_b")],
            [row(2, 11, "abc_b"), row(3, 12, "abc_a")],
            [row(3, 12, "abc_a")],
        ]
        with patch.object(c, "AC_PAGE_SIZE", 2), patch.object(c, "get_json", side_effect=pages), patch.object(c.time, "sleep"):
            self.assertEqual(c.atcoder_count(FakeSession()), 2)

    def test_atcoder_stalled_cursor_is_failure(self):
        pages = [[{"id": 1, "epoch_second": 0, "problem_id": "x", "result": "AC"},
                  {"id": 2, "epoch_second": 0, "problem_id": "y", "result": "AC"}]]
        with patch.object(c, "AC_PAGE_SIZE", 2), patch.object(c, "get_json", side_effect=pages):
            with self.assertRaisesRegex(ValueError, "stalled"):
                c.atcoder_count(FakeSession())

    def test_luogu_profile_count(self):
        with patch.object(c, "get_json", return_value={
            "currentData": {"user": {"uid": 378195, "passedProblemCount": 931}}}):
            self.assertEqual(c.luogu_count(FakeSession()), 931)
        with patch.object(c, "get_json", return_value={"currentData": {"user": {"uid": 378195}}}):
            with self.assertRaises(ValueError):
                c.luogu_count(FakeSession())

    def test_orac_reads_exact_date(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / "data" / "orac"
            path.mkdir(parents=True)
            (path / "2026-11-07.json").write_text(json.dumps({
                "date": "2026-11-07", "captured_at": "2026-11-07T11:00:00Z",
                "data": {"overall": {"icaijy": 573}}}), encoding="utf-8")
            self.assertEqual(c.orac_count(root, "2026-11-07"), (573, "2026-11-07T11:00:00Z"))
            with self.assertRaises(FileNotFoundError):
                c.orac_count(root, "2026-11-08")

    def test_missing_source_is_unavailable_then_retry_without_overwrite(self):
        now = datetime(2026, 11, 7, 2, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            with patch.object(c, "orac_count", side_effect=FileNotFoundError("not yet")), \
                 patch.object(c, "codeforces_count", return_value=4), \
                 patch.object(c, "atcoder_count", side_effect=RuntimeError("blocked")), \
                 patch.object(c, "luogu_count", return_value=10):
                initial = c.run(root=root, now=now)
            self.assertEqual(initial["platforms"]["orac"]["status"], "unavailable")
            self.assertIsNone(initial["platforms"]["orac"]["count"])
            self.assertEqual(initial["platforms"]["codeforces"]["count"], 4)
            with patch.object(c, "orac_count", return_value=(573, "2026-11-07T01:00:00Z")), \
                 patch.object(c, "codeforces_count", side_effect=AssertionError("should be skipped")), \
                 patch.object(c, "atcoder_count", return_value=7), \
                 patch.object(c, "luogu_count", side_effect=AssertionError("should be skipped")):
                updated = c.run(root=root, now=now)
            self.assertEqual(updated["platforms"]["orac"]["count"], 573)
            self.assertEqual(updated["platforms"]["atcoder"]["count"], 7)
            self.assertEqual(updated["platforms"]["codeforces"]["count"], 4)
            index = json.loads((root / "data" / "oi-daily" / "index.json").read_text())
            self.assertEqual(index["dates"], ["2026-11-07"])


if __name__ == "__main__":
    unittest.main()
