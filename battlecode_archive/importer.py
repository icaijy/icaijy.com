"""Database-only import; never execute game plugins on the site server."""
from django.db import transaction
from .ingest import load_archive, InvalidArchive
from .models import BattleSeason, BattleMatch


def import_bytes(raw: bytes, *, replace=False) -> BattleSeason:
    result = load_archive(raw)  # fully validate before touching database
    slug = result['slug']
    with transaction.atomic():
        previous = BattleSeason.objects.filter(slug=slug)
        if previous.exists():
            if not replace:
                raise InvalidArchive(f'Season {slug} already exists; supply --replace to overwrite')
            previous.delete()
        report = result['report']
        season = BattleSeason.objects.create(
            slug=slug, title=result['title'], version=result['version'],
            rules_markdown=result['rules'], viewer_html=result['viewer'],
            original_archive=result['bundle'], leaderboard=report['leaderboard'],
            participants=report['participants'], bot_sources=result['sources'],
            seed_list=report['seed_list'], played_at=report.get('created_at',''),
            metadata={'schema':report['schema'], 'scoring':report.get('scoring',''),
                      'judge_sha256':report.get('judge_sha256',''),
                      'adapter_sha256':report.get('adapter_sha256',''),
                      'matches_total':report['matches_total']})
        BattleMatch.objects.bulk_create([
            BattleMatch(season=season, **m) for m in result['records']
        ], batch_size=100)
        return season
