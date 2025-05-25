#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import argparse
import datetime
import requests
from bs4 import BeautifulSoup

AUTO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_data.json')
MANUAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_data.json')


def fetch_leaderboard():
    """Fetch and parse the ORAC Leaderboards page."""
    url = 'https://orac2.info/hub/leaderboards/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        raise RuntimeError(f'Failed to fetch page (HTTP {resp.status_code})')
    soup = BeautifulSoup(resp.text, 'html.parser')

    result = {}

    # --- overall ---
    overall_div = soup.find(id='overall')
    if overall_div is None:
        raise RuntimeError('Could not find overall leaderboard section')
    ov = {}
    for li in overall_div.select('ul.leaderboard-grid > li'):
        user = li.select_one('.username-field').get_text(strip=True)
        cnt = int(li.select_one('.solvecount').get_text(strip=True))
        ov[user] = cnt
    result['overall'] = ov

    # --- recent: week / month / year ---
    recent_div = soup.find(id='recent')
    if recent_div is None:
        raise RuntimeError('Could not find recent leaderboard section')
    rec = {}
    # h3 tags label each sub‑section
    for h3 in recent_div.find_all('h3'):
        title = h3.get_text(strip=True).lower()
        if 'week' in title:
            key = 'week'
        elif 'month' in title:
            key = 'month'
        elif 'year' in title:
            key = 'year'
        else:
            continue

        section = {}
        # iterate siblings until next <h3>
        for sib in h3.find_next_siblings():
            if getattr(sib, 'name', None) == 'h3':
                break
            if getattr(sib, 'name', None) != 'li':
                continue
            user = sib.select_one('.username-field').get_text(strip=True)
            cnt = int(sib.select_one('.solvecount').get_text(strip=True))
            section[user] = cnt

        rec[key] = section

    result['recent'] = rec
    return result


def save_auto(payload):
    """Overwrite auto_data.json with just the raw payload."""
    with open(AUTO_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'[AUTO] Wrote {AUTO_FILE} at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')


def save_manual(payload):
    """Overwrite manual_data.json, wrapping payload with a timestamp."""
    with open(MANUAL_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    last_updated_str = data.get("last_updated")
    last_updated = datetime.datetime.strptime(last_updated_str, "%Y-%m-%d %H:%M:%S")
    now = datetime.datetime.now()

    diff = now - last_updated
    if diff <= datetime.timedelta(seconds=30):
        print(f'Did not update. Reason: the most recent update was in 30s.')
        return
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    wrapper = {
        'last_updated': now,
        'data': payload
    }
    with open(MANUAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)
    print(f'[MANUAL] Wrote {MANUAL_FILE} (last_updated: {now})')


def main(mode):
    try:
        data = fetch_leaderboard()
    except Exception as e:
        print(f'ERROR fetching leaderboard: {e}', file=sys.stderr)
        return False
    try:
        if mode == 'auto':
            save_auto(data)
        elif mode == 'manual':
            save_manual(data)
        else:
            print(f"ERROR: unknown mode '{mode}'", file=sys.stderr)
            return False
    except Exception as e:
        print(f'ERROR writing file: {e}', file=sys.stderr)
        return False
    return True

if __name__ == '__main__':
    main('auto')



