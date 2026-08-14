# icaijy.com's source code

[icaijy.com](https://icaijy.com)

## Production notes

- The retired OJ is controlled by `OJ_ENABLED` and defaults to `False`. Its code and database tables remain intact.
- The 67 Counter uses the published MediaPipe Tasks Vision `1.0.1` browser bundle. It asks for camera permission before loading the pose runtime, and falls back from jsDelivr to unpkg if one CDN is filtered.
- Hall of Fame videos require `ffprobe` (provided by the `ffmpeg` system package) for server-side duration/stream validation.
- Recordings are written to `PRIVATE_MEDIA_ROOT` (default: `private_media/`). Do **not** expose that directory as a public nginx/static alias; videos are served through a permission-checking Django route.
- Enforce `client_max_body_size 26M;` (or the equivalent at the reverse proxy) in addition to the application-level 25 MiB limit.
- Hall of Fame uploads require a logged-in account and are limited per account. For production, configure `TURNSTILE_SITE_KEY` and `TURNSTILE_SECRET_KEY` to add Cloudflare Turnstile with mandatory server-side verification.
- Deleting a Hall of Fame entry in Django admin also deletes its private recording. Periodically remove rejected/stale pending entries to reclaim disk space.

Deploy database/static changes with:

```sh
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check --deploy
```
