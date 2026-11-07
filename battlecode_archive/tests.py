import io
import json
import zipfile
from django.test import TestCase
from django.urls import reverse
from .ingest import load_archive, InvalidArchive
from .importer import import_bytes
from .models import BattleSeason, BattleMatch


def make_zip(corrupt=False):
    report = {
      'schema':1, 'season':'hello', 'title':'Test Tournament', 'version':'1',
      'matches_total':1, 'seed_list':[7], 'scoring':'wins', 'created_at':'2026-11-07T02:00:00+00:00',
      'leaderboard':[{'id':'human','label':'Human','rank':1,'wins':1,'draws':0,'losses':0,'match_points':1,'score_diff':1},
                     {'id':'ai','label':'AI','rank':2,'wins':0,'draws':0,'losses':1,'match_points':0,'score_diff':-1}],
      'participants':[{'id':'human','kind':'human'}, {'id':'ai','kind':'ai'}],
      'matches':[{'index':0,'seed':7,'bot_ids':['human','ai'],'bot_names':['Human','AI'],
                  'scores':[1,0],'winner':0,'replay':'replays/match_0000.json'}],
    }
    replay = {'frames':[{'tick':0}], 'result':{'seed':7,'bot_ids':['human','ai'],
        'scores':[2,0] if corrupt else [1,0],'winner':0}}
    mem=io.BytesIO()
    with zipfile.ZipFile(mem,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('tournament.json',json.dumps(report))
        z.writestr('season/manifest.json',json.dumps({'id':'hello','version':'1'}))
        z.writestr('season/RULES.md','# Rules')
        z.writestr('season/viewer.html','<html><script>window.addEventListener("message",()=>{})</script></html>')
        z.writestr('replays/match_0000.json',json.dumps(replay))
        z.writestr('sources/human.cpp','// Test source')
    return mem.getvalue()


class ArchiveTests(TestCase):
    def test_import_and_public_pages(self):
        season = import_bytes(make_zip())
        self.assertEqual(season.matches.count(),1)
        self.assertEqual(season.bot_sources['human'],'// Test source')
        response=self.client.get(reverse('battlecode_archive:index'))
        self.assertContains(response,'Test Tournament')
        response=self.client.get(reverse('battlecode_archive:detail',args=['hello']))
        self.assertContains(response,'Every match')
        response=self.client.get(reverse('battlecode_archive:match',args=['hello',0]))
        self.assertContains(response,'battle-replay')
        response=self.client.get(reverse('battlecode_archive:viewer',args=['hello']))
        self.assertIn('sandbox allow-scripts',response['Content-Security-Policy'])
        self.assertNotIn('allow-same-origin',response['Content-Security-Policy'])
        response=self.client.get(reverse('battlecode_archive:replay',args=['hello',0]))
        self.assertEqual(response.json()['result']['winner'],0)
        season.is_public=False
        season.save()
        self.assertEqual(self.client.get(reverse('battlecode_archive:match',args=['hello',0])).status_code,404)

    def test_validation_and_duplicate_protection(self):
        with self.assertRaises(InvalidArchive): import_bytes(make_zip(corrupt=True))
        self.assertEqual(BattleSeason.objects.count(),0)
        import_bytes(make_zip())
        with self.assertRaises(InvalidArchive): import_bytes(make_zip())
        self.assertEqual(BattleSeason.objects.count(),1)
        import_bytes(make_zip(), replace=True)
        self.assertEqual(BattleMatch.objects.count(),1)

    def test_traversal(self):
        mem=io.BytesIO()
        with zipfile.ZipFile(mem,'w') as z:z.writestr('../oops','x')
        with self.assertRaises(InvalidArchive):load_archive(mem.getvalue())
