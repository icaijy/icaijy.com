import pytz
import datetime
import sys
from . import scraper

def autoupdate():
    now = datetime.datetime.now(pytz.timezone('Australia/Melbourne')).isoformat()
    print(f"[autoupdate] Running at {now}")
    sys.stdout.flush()

    try:
        scraper.main("auto")
        print("[autoupdate] Success")
    except Exception as e:
        print(f"[autoupdate] Failed: {e}", file=sys.stderr)
    sys.stdout.flush()