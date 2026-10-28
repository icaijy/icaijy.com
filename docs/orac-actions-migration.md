# Switch the ORAC daily baseline to GitHub Actions

GitHub Actions now owns daily collection. The website reads the latest public
snapshot directly from GitHub; it does not need a daily `git pull` or server
scheduler. Current standings still refresh on visits, so the live board can show
changes since the recorded snapshot. This is not a midnight-to-now counter: the
comparison capture time is printed on the page.

## 1. Deploy once

In the existing server checkout and its normal Python environment:

```sh
git pull --ff-only
python manage.py collectstatic --noinput
python manage.py check
```

Reload/restart the existing Django application service using your normal deployment
method. No database migration or new secret is needed. Keep the cron entry until
the deployment verification below passes.

## 2. Verify GitHub and the actually running website

```sh
python manage.py verify_orac_actions
```

Default target: `https://icaijy.com`. To check a different deployed origin:

```sh
python manage.py verify_orac_actions --site-url https://www.icaijy.com
```

The command checks:

1. GitHub's public `index.json` and latest snapshot are reachable directly,
   structurally valid, and captured within the last 36 hours. It does not use a
   local or Django-cache fallback for this check.
2. The running site's `/orac-leaderboards/actions-status/` reports the new
   provider, no cron dependency, and exactly the latest snapshot fingerprint.
3. The actual `/orac-leaderboards/` HTML reports the same provider and fingerprint,
   so an old process or CDN-cached page cannot pass merely because local code
   or the collector works.

Success exits with status 0 and prints:

```text
READY TO DISABLE LEGACY ORAC CRON.
```

Failure exits nonzero. A 404 normally means the running service still has old
code; deploy/reload it. If the snapshot changed during the check, or the site's
five-minute cache still holds the previous snapshot, wait five minutes and rerun.
A stale archive requires checking **GitHub → Actions → ORAC daily snapshots**;
run the workflow manually if needed. A successful manual run confirms collection
and publishing, not a guarantee that every future scheduled run will be punctual.

You can also inspect the status URL in a browser. The command remains the full
verification, because it compares that endpoint and the real page to GitHub.

## 3. Back up and disable only the legacy ORAC entry

Run this as the Linux user that owns the existing cron entry:

```sh
crontab -l
```

If it lists the ORAC job, the following verifies again, backs up the current
crontab, and only then opens the editor:

```sh
python manage.py verify_orac_actions && \
  crontab -l > "$HOME/crontab-before-orac-actions-$(date +%Y%m%d-%H%M%S).txt" && \
  crontab -e
```

Comment out the ORAC collector line with `#`, leaving unrelated jobs untouched.
It may invoke `orac_tracker/scraper.py`, `python -m orac_tracker.scraper`, or a
wrapper calling `orac_tracker.tasks.autoupdate`. If another user, system cron,
or a service timer owns the job, disable that specific entry in its original
location; editing your own crontab will not affect it.

The legacy `tasks.autoupdate()` is now a no-op. A forgotten cron that invokes the
old scraper script may still write `auto_data.json`, but that file is no longer
read by the website. The workflow remains responsible for daily records.

## 4. Confirm after disabling

```sh
python manage.py verify_orac_actions
```

Also check the Actions tab after the next scheduled collection to confirm the
schedule is continuing. Snapshot dates and capture times are visible on the live
and history pages. Missing days are not fabricated; missing users are not assumed
to have zero solved problems.

The baseline cache file defaults to `orac_tracker/github_baseline.json`, already
ignored by Git. It can be overridden in Django settings with
`ORAC_BASELINE_CACHE_FILE`. If the application cannot write it, it continues with
in-memory caching and the deployed checkout fallback, and logs the write failure.
