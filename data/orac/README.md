# Public ORAC leaderboard snapshots

One JSON snapshot per Melbourne calendar day, starting when this collector was enabled.
The first successful capture of a day is retained; reruns do not overwrite it.
`index.json` lists all available dates in ascending order. Missing dates are gaps,
not zero scores. No historical data is reconstructed.

The GitHub Actions workflow runs at **12:17 UTC** (22:17 AEST / 23:17 AEDT),
and can also be run manually. GitHub may delay scheduled jobs. Failed scrapes
fail the job without writing an empty snapshot. GitHub may disable schedules in
inactive public repositories; check the Actions tab if snapshots stop appearing.

Each `YYYY-MM-DD.json` contains:

- `schema_version`: currently 1.
- `date`, `timezone`: calendar date and `Australia/Melbourne`.
- `captured_at`: actual capture timestamp in UTC.
- `source`: public source URL.
- `data.overall`: username → total solved count, in leaderboard order.
- `data.recent.week`, `.month`, `.year`: username → rolling-period solved count.

These are **only the users shown on ORAC's public leaderboards**, not a complete
user or submission database. A missing username does not mean zero solved.
Recent counters use rolling windows, so their day-to-day difference is not a
count of newly solved problems. Tied users retain source order.

Data source: [AMT / ORAC](https://orac2.info/hub/leaderboards/).
This repository publishes snapshots for transparent access; it does not claim
ownership of the source data or grant a new licence over it.

Run locally without Django or site credentials:

```sh
python -m pip install requests==2.32.3 beautifulsoup4==4.10.0
python -m orac_tracker.snapshots
```
