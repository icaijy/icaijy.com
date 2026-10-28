"""Legacy scheduler compatibility; daily collection now runs in GitHub Actions."""
import logging


def autoupdate():
    logging.getLogger(__name__).warning(
        'Legacy ORAC autoupdate is disabled. Remove its cron/scheduler entry; '
        'daily snapshots are collected by GitHub Actions.'
    )
    return False
