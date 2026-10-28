# icaijy.com's source code

[icaijy.com](https://icaijy.com)

## Production notes

- The retired OJ is controlled by `OJ_ENABLED` and defaults to `False`. Its code and database tables remain intact.
- The 67 Counter uses the published MediaPipe Tasks Vision `1.0.1` browser bundle. It asks for camera permission before loading the pose runtime, and falls back from jsDelivr to unpkg if one CDN is filtered.
- Counter CSS and JavaScript URLs are cache-busted in the template. If a browser still requests the nonexistent `@mediapipe/tasks-vision@0.10.26/+esm`, production is serving a stale collected static file: run `collectstatic`, reload the static server, and purge any reverse-proxy/CDN cache.
- Hall of Fame videos require `ffprobe` for server-side duration/stream validation. On Raspberry Pi OS, Debian, or Ubuntu, install it with `sudo apt update && sudo apt install ffmpeg`, then verify with `ffprobe -version`.
- Recordings are written to `PRIVATE_MEDIA_ROOT` (default: `private_media/`). Do **not** expose that directory as a public nginx/static alias; videos are served through a permission-checking Django route.
- Enforce `client_max_body_size 26M;` (or the equivalent at the reverse proxy) in addition to the application-level 25 MiB limit.
- Hall of Fame uploads may be anonymous. Logged-in runs retain ownership and can be downloaded or deleted from `/67/hall-of-fame/mine/`; anonymous runs cannot be claimed or managed later.
- For production, configure `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` to add Cloudflare Turnstile with mandatory server-side verification.
- Anonymous uploads require Turnstile whenever `DEBUG=False`; authenticated uploads remain available if Turnstile is not configured. Local `DEBUG=True` development allows anonymous testing without an external challenge.
- The default Hall of Fame rate limit is 3 attempts per authenticated account or anonymous network key in a rolling minute. Failed Turnstile, score, and video-validation attempts count too; override it with `HOF_SUBMISSIONS_PER_MINUTE`.
- Anonymous network keys are HMAC hashes; raw IP addresses are not stored. The default source is `REMOTE_ADDR`. Behind a trusted proxy, set `HOF_TRUSTED_IP_HEADER=HTTP_CF_CONNECTING_IP` (Cloudflare) or the appropriate server-populated WSGI header. Never trust a client-spoofable forwarding header at an exposed origin.
- Valid Hall of Fame uploads are published immediately. Delete obvious fake or abusive entries in Django admin; deleting an entry also deletes its private recording.

Deploy database/static changes with:

```sh
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```

## Archive and ORAC daily history

- `/archive/` groups the older 67 / VCE projects. Existing routes, database
  records and recordings are retained; no database migration is required.
- The existing **server midnight scrape remains unchanged**: `scraper.main('auto')`
  / `tasks.autoupdate()` still write `orac_tracker/auto_data.json`, used by the
  live page for its original daily baseline. Do not remove the server cron.
- Independently, `.github/workflows/orac-daily.yml` collects the public ORAC
  boards once per day and commits `data/orac/YYYY-MM-DD.json` plus `index.json`.
  It uses the public repository's standard Ubuntu runner, no paid larger runner,
  no Actions artifacts/cache, and no personal access token.
- `/orac-leaderboards/history/` reads that public archive from GitHub with a
  five-minute cache, falling back to the deployed checkout if GitHub is down.
  It does not require a daily website deployment to show newly recorded days.
- See [data format and limitations](data/orac/README.md). The archive and live
  baseline have different capture times and are deliberately independent.
- For a manual collection use **Actions → ORAC daily snapshots → Run workflow**.
  If repository rules disallow the workflow's commit, the job fails visibly;
  a maintainer must allow the bot to write `data/orac/`. Account-wide Actions
  restrictions can also prevent execution even though this public runner is free.

For an existing server deployment, pull the updated code, run `collectstatic`
using the commands above, and reload the existing application service. This
repository does not contain server SSH credentials or an automatic deployment
workflow; a GitHub update alone does not confirm the server was reloaded.
