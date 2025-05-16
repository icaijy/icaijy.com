#!/usr/bin/env python3
import datetime
import os
import sys
import pytz
import subprocess

def main():
    tz = pytz.timezone('Australia/Melbourne')
    now = datetime.datetime.now(tz)
    print(f"{now.isoformat()} START")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    scraper_path = os.path.join(script_dir, "orac_tracker", "scraper.py")

    # 用 subprocess.run 传列表，绝对不会有路径拆分问题
    result = subprocess.run(
        [sys.executable, scraper_path, "auto"],
        check=False
    )

    if result.returncode != 0:
        print(f"{datetime.datetime.now(tz).isoformat()} Scraper exited with code {result.returncode}")

    print(f"{datetime.datetime.now(tz).isoformat()} ---")

if __name__ == "__main__":
    main()
