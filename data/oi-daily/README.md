# Daily OI solved-count snapshots

This independent collector monitors the public account `icaijy` across **Codeforces, AtCoder, Luogu (UID 378195), and ORAC** without modifying the Django site or OI Training Site.

## Data and cadence

The GitHub Action runs at **12:42 UTC each day** (22:42 AEST / 23:42 AEDT). GitHub may delay scheduled workflows. Files are labelled with the **actual Australia/Melbourne date at collection time**, not the scheduled date:

- `data/oi-daily/index.json`: available snapshot dates.
- `data/oi-daily/YYYY-MM-DD.json`: each platform's cumulative distinct solved count, exact sampling time, data source, and availability status.

On a retry, the first successful sample per platform on each date is preserved. Unavailable sources may be retried. A failed request never becomes a zero count.

**An adjacent snapshot difference is a net count change between two sample times**, not necessarily all ACs made during the midnight-to-midnight calendar day. The first sample is a baseline, never a +N day. If either snapshot lacks a platform, that day's delta is **unknown**, not 0. Do not silently bridge missing dates and call the result a one-day total. A negative delta may occur if a platform changes its data.

## Sources

- Codeforces: official `user.status` API, paginated and deduplicated by contest ID and problem index.
- AtCoder: AtCoder Problems public v3 submission API, paginated with timestamp overlap and deduplicated by problem ID. The provider recommends waiting over 1 second between calls.
- Luogu: public user profile `passedProblemCount` via `?_contentOnly`. Private/blocked/changed APIs are marked unavailable. This is not an official stable API.
- ORAC: reads the **existing** local snapshot for the same Melbourne date in `data/orac/YYYY-MM-DD.json`, using `data.overall.icaijy` and its original `captured_at`. These records are independently maintained by the existing `orac-daily.yml` job. An ORAC snapshot captured early in the day cannot be interpreted as end-of-day activity.

Counts are per platform; they are **not de-duplicated across platforms** (some problems appear on more than one site).

## Run or test locally

```sh
python -m pip install requests==2.32.3
python -m unittest discover -s oi_daily -p 'test_*.py'
python -m oi_daily.collector
```

The collector is read-only with respect to external sites. It writes only local JSON files under `data/oi-daily/`. GitHub Actions commits these files. No credentials or API keys are needed.

If a platform fails, check the `status` and `error` fields in the snapshot and the workflow logs before changing the collector. Do not treat a blocked API as a day with zero training. GitHub Actions or platform rate limits may temporarily prevent complete results.
