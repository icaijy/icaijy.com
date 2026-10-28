#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import json
import datetime
import requests
from bs4 import BeautifulSoup

AUTO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auto_data.json')
MANUAL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_data.json')


def fetch_leaderboard():
    """Fetch and parse the ORAC Leaderboards page."""
    url = 'https://orac2.info/hub/leaderboards/'
    headers = {'User-Agent': 'Mozilla/5.0'}
    resp = requests.get(url, headers=headers, timeout=(5, 25))
    if resp.status_code != 200:
        raise RuntimeError(f'Failed to fetch page (HTTP {resp.status_code})')
    return parse_leaderboard(resp.text)


def parse_leaderboard(html):
    soup = BeautifulSoup(html, 'html.parser')

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
    validate_payload(result)
    return result


def validate_payload(payload):
    """Reject error pages / partial parses before they can enter the archive."""
    if not isinstance(payload, dict) or not isinstance(payload.get('recent'), dict):
        raise ValueError('Invalid leaderboard payload')
    boards = [payload.get('overall')]
    for period in ('week', 'month', 'year'):
        if period not in payload['recent']:
            raise ValueError(f'Missing {period} leaderboard')
        boards.append(payload['recent'][period])
    for index, board in enumerate(boards):
        if not isinstance(board, dict) or (index == 0 and not board):
            raise ValueError('Missing overall leaderboard or invalid board')
        for username, count in board.items():
            if not isinstance(username, str) or not username or type(count) is not int or count < 0:
                raise ValueError('Invalid leaderboard entry')


def save_auto(payload):
    """Overwrite auto_data.json with just the raw payload."""
    with open(AUTO_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f'[AUTO] Wrote {AUTO_FILE} at {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')


def save_manual(payload):
    """Overwrite manual_data.json, wrapping payload with a timestamp."""
    now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    wrapper = {
        'last_updated': now_str,
        'data': payload
    }
    with open(MANUAL_FILE, 'w', encoding='utf-8') as f:
        json.dump(wrapper, f, ensure_ascii=False, indent=2)
    print(f'[MANUAL] Wrote {MANUAL_FILE} (last_updated: {now_str})')


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
    sys.exit(0 if main('auto') else 1)
