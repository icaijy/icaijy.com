# icaijy.com's source code

[icaijy.com](https://icaijy.com)

## Production notes

- The retired OJ is controlled by `OJ_ENABLED` and defaults to `False`. Its code and database tables remain intact.
- The 67 Counter uses the published MediaPipe Tasks Vision `1.0.1` browser bundle. It asks for camera permission before loading the pose runtime, and falls back from jsDelivr to unpkg if one CDN is filtered.
- Counter CSS and JavaScript URLs are cache-busted in the template. If a browser still requests the nonexistent `@mediapipe/tasks-vision@0.10.26/+esm`, production is serving a stale collected static file: run `collectstatic`, reload the static server, and purge any reverse-proxy/CDN cache.
- Hall of Fame videos require `ffprobe` for server-side duration/stream validation. On Raspberry Pi OS, Debian, or Ubuntu, install it with `sudo apt update && sudo apt install ffmpeg`, then verify with `ffprobe -version`.
- Recordings are written to `PRIVATE_MEDIA_ROOT` (default: `private_media/`). Do **not** expose that directory as a public nginx/static alias; videos are served through a permission-checking Django route.
- Enforce `client_max_body_size 26M;` (or the equivalent at the reverse proxy) in addition to the application-level 25 MiB limit.
- Hall of Fame uploads require a logged-in account and are limited per account. For production, configure `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` to add Cloudflare Turnstile with mandatory server-side verification.
- The default Hall of Fame rate limit is 3 attempts per authenticated account in a rolling hour. Failed Turnstile, score, and video-validation attempts count too; override it with `HOF_SUBMISSIONS_PER_HOUR`.
- Valid Hall of Fame uploads are published immediately. Delete obvious fake or abusive entries in Django admin; deleting an entry also deletes its private recording.

Deploy database/static changes with:

```sh
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```
