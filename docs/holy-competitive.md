# 🥶 holy competetive

URL: `/holy-competitive/`. The homepage and navigation link to it.
This is the existing Django application, deployed from this Git repository;
there is no Sites dependency or new hosting service.

## Deploy on the existing server

Back up the existing SQLite database using the server's normal backup procedure,
then run from the existing checkout and virtual environment:

```sh
git pull --ff-only origin main
python -m pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
python manage.py check
```

Reload the existing Django/Gunicorn service using its existing service name.
**The collector must also run**; a website reload alone does not start it.
No Redis, Celery worker, paid service, API keys, or browser login is required.

### Run the collector persistently

Try it in the foreground first:

```sh
python manage.py holy_worker --once
python manage.py holy_status
```

`--once` tries **one** request and exits. Running it again immediately prints
that the corresponding upstream request budget has not recovered (unless another host is ready). For continuous collection:

```sh
python manage.py holy_worker
```

For production, install a systemd unit using **the same Unix account and checkout
as the web service**, so both can write the SQLite database and its directory.
Adapt the three example paths/account names below to the actual deployment:

```ini
# /etc/systemd/system/icaijy-holy.service
[Unit]
Description=icaijy Holy Competitive cache collector
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/srv/icaijy.com
ExecStart=/srv/icaijy.com/venv/bin/python manage.py holy_worker
Environment=PYTHONUNBUFFERED=1
Restart=on-failure
RestartSec=15
UMask=0007

[Install]
WantedBy=multi-user.target
```

Django already reads the checkout's `.env`; use the same production configuration
as the web service. Do not start this against a different database or checkout.
Then enable and inspect it:

```sh
sudo systemctl daemon-reload
sudo systemctl enable --now icaijy-holy.service
sudo systemctl status icaijy-holy.service
sudo journalctl -u icaijy-holy.service -n 30 --no-pager
python manage.py holy_status --check
```

Alternatively an existing server scheduler can call `holy_worker --once` every
minute. **Choose one method**, not both. The database gate and local file lock
still prevent simultaneous collectors from exceeding the upstream budget.
A second server with a separate database is a separate collector; don't run one.
The ignored `holy-collector.lock` file must be writable by the collector user.

After starting the worker, visit `/holy-competitive/`, submit handles, and watch
its status. A query has priority over ordinary peer updates. The first query
requires a lifetime backfill; an AtCoder account not found in the roster also
needs a separate profile verification request. A nonexistent account is shown
as an upstream error and retried with backoff, never silently treated as empty.

`holy_status --check` checks worker heartbeat only, not completion of the entire
roster. The page separately reports total/synced/fresh accounts, pending requests,
oldest completed cache, and metadata/roster failures. Verify those before treating
the initial problem list as complete. This repository has no SSH credentials or
automatic server deployment: pushing Git alone does not confirm a live reload.

## Data semantics

- CF: official `user.ratedList(activeOnly=false, includeRetired=true)`, country
  exactly `Australia`, **current rating >= 1200**, including inactive users.
- AtCoder: public `/ranking/all?contestType=algo&f.Country=AU&f.RatingLowerBound=1200`,
  including inactive users, following all pagination. Current algorithm rating
  >= 1200. A failed/partial roster refresh never retires unseen old users.
- This is self-declared profile country, not verified nationality/residence.
  Two platform handles are independent; no inferred cross-platform identity.
- Candidates: peer accounts' **public submissions within a rolling 30 days**,
  including contests and practice. Distinct handles count once per problem.
  Both public ACs and unsuccessful submissions are included. “Trying” means
  submissions observed with no cached AC, not a claim the user is currently online.
  Peers start with 30-day histories; an AC before the initial coverage may be unknown.
- “Recent AC” counts accepted submissions timestamped within those 30 days.
  A known earlier AC with a recent resubmission is separately labelled. It is
  neither a new recent AC nor an unsolved attempt.
- For queried handles, **all-time AC history** is fetched, paginated and cached.
  Until this completes, comparison results are withheld. Afterwards all historical
  ACs are excluded, even if they occurred years ago. New ACs after `synced_at`
  can remain in results until the next refresh. This is a snapshot, not live state.
- Difficulty descending, unknown difficulties last; ties use peer count then
  problem ID. Platforms are separate because their scales are different.
  CF uses official problem ratings/tags. AtCoder uses AtCoder Problems estimated
  difficulty with its standard below-400 display conversion, not an official rating.
- Refresh roster/catalogs daily; resync peers daily; queried handles remain on
  daily refresh for seven days after last query. A user can request a refresh
  after six hours. Failed requests retain successful data and retry exponentially.
  Old failed-only activity is pruned after 35 days; cached ACs remain for exclusion.
  Rejudging old submissions outside the overlap window can leave historical cache
  verdicts stale; private or deleted submissions cannot be inferred.

## Queue and upstream request policy

- Each job/page does **one** HTTP request. Independent persistent budgets start
  after each job finishes: **CF API 2.1 seconds**, **AtCoder Problems 1.1 seconds**,
  and **AtCoder ranking/profile HTML 3 seconds**. CF documents one request per
  two seconds; AtCoder Problems asks for more than one second between accesses.
  AtCoder HTML has no verified published request quota, so it keeps a separate
  conservative interval. These intervals leave a small margin over API limits.
- HTTP redirects and automatic retries are disabled. Errors consume their slot.
  Failed hosts pause for 30 seconds, doubling on consecutive failures (up to
  7680 seconds); both `Retry-After` formats can extend that pause. The failed job
  also backs off. Other hosts continue: a cooling high-priority CF job cannot
  block ready AtCoder work. Successful requests reset that host's failure count.
- The worker remains serial, with short polling while work is pending and a
  five-second idle sleep. It does not continuously hit upstreams when caches are
  fresh. Daily refresh schedules are unchanged. Run the continuous worker to
  reach API-paced throughput; cron every minute is still safe but much slower.
- On upgrade, a migration carries any outstanding old shared cooldown into the
  new host budgets, so an existing `Retry-After` is not silently discarded.
  Stop the old worker, migrate, then restart it; do not mix worker versions.
- A database lease plus a nonblocking Unix `flock` prevents concurrent workers;
  a crash preserves pages and leaves a conservative 15-minute lease before retry.
- Jobs and account/problem aggregates survive restarts in SQLite. Unique job keys
  deduplicate repeated requests. Page cursors persist; upserts make replay safe.
  Web requests only read cache or enqueue comparisons; no upstream HTTP, thread
  spawning, or eager Celery tasks run inside WSGI.
- Queried handles receive higher priority, with pages rotating at the end of
  their priority class. In-flight peer jobs keep their cursors before backfilling.
  An IP-hour HMAC budget admits at most 20 query form submissions/hour; raw IPs
  aren't stored. Only `REMOTE_ADDR` is trusted, so a reverse proxy can share this
  budget across visitors. The pending user-job queue is capped at 1000.
- CF's all-user roster is currently about 350 MB per refresh. `ijson` streams and
  filters it so the global user list is never loaded into RAM; bandwidth still
  costs roughly that much per day. No submission source code is downloaded.
- Observed during implementation: 253 qualifying CF users and 86 AtCoder users.
  The previous artificial 17-hour spacing is removed. With one page/user, the
  sum of the new per-request waits is about 10.5 minutes before interleaving;
  network/processing time, the large roster transfer, history pagination, and
  retries add time. This is not an end-to-end completion estimate. The page
  labels coverage and actual completion times.
- AtCoder Problems returns at most 500 submissions per call. Its inclusive-second
  cursor is overlapped on page boundaries; a fully saturated single second that
  cannot advance fails explicitly rather than dropping data/claiming completion.
  Periodic sync overlaps the last observed day to pick up pending verdicts.

Upstream references:

- https://codeforces.com/robots.txt — the collector only uses `/api/`, not ratings/submission HTML.
- https://atcoder.jp/robots.txt — ranking/profile discovery only; no direct scraping of disallowed submissions or history pages.
- https://codeforces.com/apiHelp — at most one API request per two seconds.
- https://codeforces.com/apiHelp/methods — rated users, user submissions, problemset.
- https://github.com/kenkoooo/AtCoderProblems/blob/main/doc/api.md — unofficial API;
  wait more than one second, 500-result user submission API, difficulty models.
- https://atcoder.jp/ranking/all?contestType=algo&f.Country=AU&f.RatingLowerBound=1200

## Checks

```sh
python manage.py test holy orac_tracker
python manage.py makemigrations --check --dry-run
python manage.py check
```

Tests cover lifetime exclusion, provisional history, platform separation,
peer counts/deduplication, sorting/filtering, both pagination orders, inclusive
AtCoder seconds, saturated boundaries, country/current-rating filtering,
partial rosters, persistent request admission, query deduplication, cache-only
GET/polling, independent host budgets, host-local backoff, restart lease, and upstream redirects.
