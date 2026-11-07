"""Read a trusted, offline Mini Battlecode result ZIP as inert data.

No game.py or C++ binary is imported/executed by the web server.
"""
from __future__ import annotations

from io import BytesIO
import json
import re
import stat
import zipfile

SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_-]{0,60}$')
MAX_UPLOAD = 80 * 1024 * 1024
MAX_UNCOMPRESSED = 200 * 1024 * 1024
MAX_MATCHES = 4000


class InvalidArchive(ValueError):
    pass


def load_archive(contents: bytes) -> dict:
    if not contents or len(contents) > MAX_UPLOAD:
        raise InvalidArchive('Archive must be nonempty and <=80 MiB')
    try:
        zf = zipfile.ZipFile(BytesIO(contents))
    except (OSError, zipfile.BadZipFile) as exc:
        raise InvalidArchive('Not a ZIP archive') from exc
    with zf as z:
        infos = z.infolist()
        names = [x.filename for x in infos]
        if (len(names) > MAX_MATCHES + 30 or len(names) != len(set(names)) or
            sum(x.file_size for x in infos) > MAX_UNCOMPRESSED):
            raise InvalidArchive('Archive has duplicate names or exceeds size limit')
        for item in infos:
            if (item.filename.startswith('/') or '\\' in item.filename or
                '..' in item.filename.split('/') or
                stat.S_ISLNK((item.external_attr >> 16) & 0xFFFF) or
                item.file_size > 8 * 1024 * 1024):
                raise InvalidArchive('Unsafe archive entry')
        def read(name, size=8 * 1024 * 1024):
            if name not in names:
                raise InvalidArchive(f'Missing archive entry: {name}')
            info = z.getinfo(name)
            if info.file_size > size:
                raise InvalidArchive(f'Oversized entry: {name}')
            try:
                data = z.read(name)
            except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
                raise InvalidArchive('Corrupt ZIP member') from exc
            if len(data) > size:
                raise InvalidArchive('ZIP content exceeds byte limit')
            return data
        def obj(name):
            try:
                value = json.loads(read(name))
            except (UnicodeError, ValueError) as exc:
                raise InvalidArchive(f'Invalid JSON: {name}') from exc
            if not isinstance(value, dict):
                raise InvalidArchive(f'Expected JSON object: {name}')
            return value
        report = obj('tournament.json')
        manifest = obj('season/manifest.json')
        slug = report.get('season')
        if (not isinstance(slug, str) or not SAFE_ID.fullmatch(slug) or
            manifest.get('id') != slug or report.get('schema') != 1):
            raise InvalidArchive('Invalid season ID or format version')
        if report.get('version') != manifest.get('version'):
            raise InvalidArchive('Season version mismatch')
        title = report.get('title')
        if not isinstance(title, str) or not 0 < len(title) <= 200:
            raise InvalidArchive('Invalid season title')
        try:
            rules = read('season/RULES.md', 500_000).decode('utf-8')
            viewer = read('season/viewer.html', 1_000_000).decode('utf-8')
        except UnicodeDecodeError as exc:
            raise InvalidArchive('Invalid UTF-8 in game description') from exc
        matches = report.get('matches')
        standings = report.get('leaderboard')
        participants = report.get('participants')
        seeds = report.get('seed_list')
        if (not isinstance(matches, list) or not isinstance(standings, list) or
            not isinstance(participants, list) or not isinstance(seeds, list) or
            not matches or len(matches) > MAX_MATCHES or
            len(matches) != report.get('matches_total')):
            raise InvalidArchive('Invalid tournament size or missing metadata')
        if len(participants) < 2 or len(participants) != len(standings):
            raise InvalidArchive('Invalid participant counts')
        IDs = [x.get('id') if isinstance(x, dict) else None for x in participants]
        if any(not isinstance(v, str) or not SAFE_ID.fullmatch(v) for v in IDs) or len(set(IDs)) != len(IDs):
            raise InvalidArchive('Invalid participant IDs')
        ids = set(IDs)
        if {s.get('id') for s in standings} != ids:
            raise InvalidArchive('Leaderboard differs from roster')
        records = []
        for ix, entry in enumerate(matches):
            if not isinstance(entry, dict) or entry.get('index') != ix:
                raise InvalidArchive('Match index sequence invalid')
            pair = entry.get('bot_ids')
            score = entry.get('scores')
            winner = entry.get('winner')
            seed = entry.get('seed')
            if (not isinstance(pair, list) or len(pair) != 2 or pair[0] == pair[1] or
                any(p not in ids for p in pair) or
                not isinstance(score, list) or len(score) != 2 or
                any(type(v) not in (int, float) or v < 0 for v in score) or
                winner not in (None, 0, 1) or type(seed) is not int or seed not in seeds):
                raise InvalidArchive(f'Invalid match metadata #{ix}')
            name = f'replays/match_{ix:04d}.json'
            if entry.get('replay') != name:
                raise InvalidArchive('Unexpected replay path')
            replay = obj(name)
            replay_result = replay.get('result')
            if (not isinstance(replay.get('frames'), list) or
                not isinstance(replay_result, dict) or
                replay_result.get('scores') != score or
                replay_result.get('winner') != winner or
                replay_result.get('bot_ids') != pair or
                replay_result.get('seed') != seed):
                raise InvalidArchive(f'Mismatching replay metadata #{ix}')
            records.append({'index': ix, 'seed': seed, 'blue': pair[0], 'red': pair[1],
                            'score_blue': score[0], 'score_red': score[1],
                            'winner': winner, 'summary': entry, 'replay': replay})
        sources = {}
        for bot_id in IDs:
            name = f'sources/{bot_id}.cpp'
            if name in names:
                try:
                    sources[bot_id] = read(name, 500_000).decode('utf-8')
                except UnicodeDecodeError as exc:
                    raise InvalidArchive('Invalid C++ source encoding') from exc
        return {'slug':slug, 'title':title, 'version':str(report['version']),
                'rules':rules, 'viewer':viewer, 'report':report,
                'sources':sources, 'records':records, 'bundle':contents}
