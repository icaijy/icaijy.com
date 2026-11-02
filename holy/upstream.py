"""Public upstreams only. Each job makes exactly one HTTP request; no retries here."""
import math
import re
from urllib.parse import parse_qs, urlparse

import ijson
import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'icaijy.com HolyCompetitive/1.0 (+https://icaijy.com/holy-competitive/)'}
CF = 'https://codeforces.com/api/'
AC = 'https://kenkoooo.com/atcoder/'


class UpstreamError(Exception):
    def __init__(self, message, retry_after=0):
        super().__init__(message)
        self.retry_after = retry_after


def fetch(url, params=None, *, stream=False):
    response = requests.get(url, params=params, headers=HEADERS, timeout=(10, 45),
                            stream=stream, allow_redirects=False)
    if response.status_code != 200:
        # Never follow redirects outside the shared request gate.
        value = response.headers.get('Retry-After', '')
        try:
            from email.utils import parsedate_to_datetime
            from django.utils import timezone
            delay = int(value) if value.isdigit() else max(0, int((parsedate_to_datetime(value) - timezone.now()).total_seconds()))
        except (ValueError, TypeError, OverflowError):
            delay = 0
        response.close()
        raise UpstreamError(f'Upstream HTTP {response.status_code}', retry_after=delay)
    return response


def cf_api(method, **params):
    with fetch(CF + method, params) as response:
        value = response.json()
    if value.get('status') != 'OK':
        raise UpstreamError(str(value.get('comment', 'Codeforces API failed'))[:200])
    return value['result']


def cf_roster():
    # ratedList is hundreds of MB. Stream objects instead of loading the global
    # user list into RAM on the website's server. Preserve inactive/retired users.
    result = []
    seen = 0
    with fetch(CF + 'user.ratedList', {'activeOnly': 'false', 'includeRetired': 'true'}, stream=True) as response:
        response.raw.decode_content = True
        for user in ijson.items(response.raw, 'result.item'):
            seen += 1
            if user.get('country') == 'Australia' and user.get('rating', 0) >= 1200:
                result.append((user['handle'], int(user['rating'])))
    if not seen or not result:
        raise UpstreamError('Codeforces roster was empty or invalid; retaining previous roster')
    return result


def parse_ac_roster(html, page):
    soup = BeautifulSoup(html, 'html.parser')
    table = next((t for t in soup.select('table') if t.select('a[href^="/users/"]')), None)
    if table is None or soup.select_one('.pagination') is None:
        raise UpstreamError('AtCoder ranking layout changed or challenge page; retaining roster')
    rows = []
    for row in table.select('tbody tr'):
        user = row.select_one('a[href^="/users/"]')
        cells = row.find_all('td', recursive=False)
        if user is None or len(cells) < 4 or not row.select('img[src$="/AU.png"]'):
            raise UpstreamError('Unexpected AtCoder ranking row')
        handle = user['href'].split('/')[-1]
        rating = int(cells[3].get_text(strip=True))
        if not re.fullmatch(r'[A-Za-z0-9_]{1,32}', handle) or rating < 1200:
            raise UpstreamError('Unexpected AtCoder ranking filter result')
        rows.append((handle, rating))
    pages = [int(parse_qs(urlparse(a.get('href', '')).query).get('page', ['1'])[0])
             for a in soup.select('.pagination a')]
    return rows, page < max(pages, default=page)


def ac_roster(page):
    with fetch('https://atcoder.jp/ranking/all', {'contestType': 'algo', 'f.Country': 'AU',
                                               'f.RatingLowerBound': 1200, 'page': page, 'lang': 'en'}) as response:
        return parse_ac_roster(response.text, page)


def ac_verify(handle):
    with fetch('https://atcoder.jp/users/' + handle, {'lang': 'en'}) as response:
        soup = BeautifulSoup(response.text, 'html.parser')
    if not soup.select_one('#rating-graph') and not soup.select_one('#user-nav-tabs'):
        raise UpstreamError('AtCoder profile could not be verified')


def ac_submissions(handle, second):
    with fetch(AC + 'atcoder-api/v3/user/submissions', {'user': handle, 'from_second': second}) as response:
        data = response.json()
    if not isinstance(data, list) or any(not isinstance(s, dict) or
            not {'id', 'epoch_second', 'problem_id', 'contest_id', 'result'} <= s.keys() for s in data):
        raise UpstreamError('Invalid AtCoder submissions response')
    return data


def ac_resource(name):
    with fetch(AC + 'resources/' + name + '.json') as response:
        return response.json()


def display_difficulty(value):
    return round(value if value >= 400 else 400 * math.exp((value - 400) / 400))
