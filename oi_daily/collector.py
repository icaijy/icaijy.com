"""Daily public AC-count snapshots for a single OI training account.

Each snapshot is a point-in-time observation, NOT an exact calendar-day ledger.
A missing or blocked source must never be recorded as zero.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests


MELBOURNE = ZoneInfo("Australia/Melbourne")
CF_PAGE_SIZE = 1000
AC_PAGE_SIZE = 500
HEADERS = {
    "User-Agent": "OIDailyTracker/1.0 (+https://github.com/icaijy/icaijy.com)",
    "Accept": "application/json",
}
SOURCE = {
    "codeforces": "https://codeforces.com/api/user.status?handle=icaijy",
    "atcoder": "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions?user=icaijy",
    "luogu": "https://www.luogu.com.cn/user/378195?_contentOnly",
    "orac": "https://orac2.info/hub/leaderboards/",
}


def get_json(session, url, *, params=None, extra_headers=None):
    """Retry transient HTTP failures, never substitute an empty JSON response."""
    for attempt in range(3):
        try:
            response = session.get(url, params=params,
                                   headers={**HEADERS, **(extra_headers or {})},
                                   timeout=(10, 40))
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                response.close()
                time.sleep(3 * (attempt + 1))
                continue
            response.raise_for_status()
            return response.json()
        except (requests.Timeout, requests.ConnectionError):
            if attempt == 2:
                raise
            time.sleep(3 * (attempt + 1))
    raise RuntimeError("HTTP retries exhausted")


def codeforces_count(session):
    """Count distinct problems ever accepted from all Codeforces submissions."""
    result = set()
    offset = 1
    for page in range(200):
        payload = get_json(
            session,
            "https://codeforces.com/api/user.status",
            params={"handle": "icaijy", "from": offset, "count": CF_PAGE_SIZE},
        )
        if not isinstance(payload, dict) or payload.get("status") != "OK":
            raise ValueError("Codeforces API response not OK")
        rows = payload.get("result")
        if not isinstance(rows, list):
            raise ValueError("Codeforces result was not a list")
        for row in rows:
            if row.get("verdict") != "OK":
                continue
            problem = row.get("problem") or {}
            index = problem.get("index")
            if not index:
                raise ValueError("Accepted Codeforces problem without index")
            contest = problem.get("contestId", row.get("contestId"))
            if contest is not None:
                key = ("contest", str(contest), str(index))
            else:
                # Some gym/legacy problems lack contestId. Keep them distinct.
                key = ("other", str(problem.get("problemsetName", "")),
                       str(index), str(problem.get("name", "")))
            result.add(key)
        if len(rows) < CF_PAGE_SIZE:
            return len(result)
        offset += len(rows)
        time.sleep(2.1)  # Codeforces API: no more than one call per two seconds.
    raise ValueError("Codeforces pagination limit reached; refusing a partial count")


def atcoder_count(session):
    """Count distinct accepted problem IDs, respecting API's 500-row page limit."""
    accepted = set()
    seen_submission_ids = set()
    cursor = 0
    for page in range(200):
        rows = get_json(
            session,
            "https://kenkoooo.com/atcoder/atcoder-api/v3/user/submissions",
            params={"user": "icaijy", "from_second": cursor},
        )
        if not isinstance(rows, list):
            raise ValueError("AtCoder API result was not a list")
        high_second = cursor
        fresh = 0
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("Invalid AtCoder submission")
            sid = int(row["id"])
            second = int(row["epoch_second"])
            if second < cursor:
                raise ValueError("AtCoder API returned rows before cursor")
            high_second = max(high_second, second)
            if sid in seen_submission_ids:
                continue
            seen_submission_ids.add(sid)
            fresh += 1
            if row.get("result") == "AC":
                accepted.add(str(row["problem_id"]))
        if len(rows) < AC_PAGE_SIZE:
            return len(accepted)
        if high_second <= cursor or fresh == 0:
            raise ValueError("AtCoder pagination stalled at timestamp boundary")
        cursor = high_second
        time.sleep(1.2)  # AtCoder Problems recommends >1s between accesses.
    raise ValueError("AtCoder pagination limit reached; refusing a partial count")


def luogu_count(session):
    """Public Luogu profile count. A private/blocked profile is unavailable."""
    payload = get_json(
        session,
        "https://www.luogu.com.cn/user/378195",
        params={"_contentOnly": "1"},
        extra_headers={"x-luogu-type": "content-only",
                       "Referer": "https://www.luogu.com.cn/"},
    )
    if not isinstance(payload, dict):
        raise ValueError("Luogu did not return a JSON object")
    user = (payload.get("currentData") or {}).get("user") or {}
    if str(user.get("uid")) != "378195":
        raise ValueError("Luogu profile UID mismatch or inaccessible")
    value = user.get("passedProblemCount")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Luogu passedProblemCount missing or invalid")
    return value


def orac_count(root, local_date):
    """Read the already-published ORAC snapshot for exactly this local date."""
    path = root / "data" / "orac" / (local_date + ".json")
    snapshot = json.loads(path.read_text(encoding="utf-8"))
    if snapshot.get("date") != local_date:
        raise ValueError("ORAC snapshot date does not match local date")
    count = ((snapshot.get("data") or {}).get("overall") or {}).get("icaijy")
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("icaijy missing from ORAC overall leaderboard")
    captured = snapshot.get("captured_at")
    if not isinstance(captured, str) or not captured:
        raise ValueError("ORAC capture time missing")
    return count, captured


def observation(count, sampled_at, source):
    if isinstance(count, bool) or not isinstance(count, int) or count < 0:
        raise ValueError("Accepted count must be a nonnegative integer")
    return {"status": "ok", "count": count, "sampled_at": sampled_at,
            "source": source}


def run(root=None, now=None):
    root = Path(root) if root is not None else Path(__file__).resolve().parent.parent
    now = now or datetime.now(timezone.utc)
    local_date = now.astimezone(MELBOURNE).date().isoformat()
    sampled_at = now.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    folder = root / "data" / "oi-daily"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (local_date + ".json")
    if path.exists():
        document = json.loads(path.read_text(encoding="utf-8"))
        if document.get("date") != local_date:
            raise ValueError("Existing snapshot has a mismatched date")
    else:
        document = {"schema_version": 1, "date": local_date,
                    "timezone": "Australia/Melbourne", "platforms": {}}
    platforms = document.setdefault("platforms", {})
    with requests.Session() as session:
        for platform in ("orac", "codeforces", "atcoder", "luogu"):
            # Preserve the first successful observation of the local day.
            if platforms.get(platform, {}).get("status") == "ok":
                continue
            try:
                if platform == "orac":
                    count, observed_at = orac_count(root, local_date)
                else:
                    count = {"codeforces": codeforces_count,
                             "atcoder": atcoder_count,
                             "luogu": luogu_count}[platform](session)
                    observed_at = sampled_at
                platforms[platform] = observation(count, observed_at, SOURCE[platform])
            except (Exception) as exc:
                # Missing dates, blocked upstreams and malformed responses are NOT 0.
                platforms[platform] = {"status": "unavailable", "count": None,
                    "sampled_at": sampled_at, "source": SOURCE[platform],
                    "error": (type(exc).__name__ + ": " + str(exc))[:220]}
    document["recorded_at"] = sampled_at
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")
    days = sorted(p.stem for p in folder.glob("????-??-??.json")
                  if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p.stem))
    index = {"schema_version": 1, "timezone": "Australia/Melbourne", "dates": days}
    (folder / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"date": local_date, "platforms": {
        p: {"status": r["status"], "count": r["count"]}
        for p, r in platforms.items()}}, ensure_ascii=False))
    return document


if __name__ == "__main__":
    run()
