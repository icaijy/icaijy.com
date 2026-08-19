from django.test import TestCase

from .models import HallOfFameComment, HallOfFameEntry


class HallOfFameOrderingTests(TestCase):
    def make_run(self, score, name):
        return HallOfFameEntry.objects.create(
            display_name=name,
            game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
            score=score,
            video=f'hall_of_fame/{name}.webm',
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

    def test_comment_annotations_never_change_score_ranking(self):
        low = self.make_run(10, 'low')
        high = self.make_run(190, 'high')
        middle = self.make_run(67, 'middle')

        # Deliberately make comment counts disagree with the score order. This is
        # the aggregation that previously caused the leaderboard regression.
        for index in range(5):
            HallOfFameComment.objects.create(
                entry=low,
                author_name=f'guest-{index}',
                body='comment',
            )
        HallOfFameComment.objects.create(entry=middle, author_name='guest', body='comment')

        response = self.client.get('/67/hall-of-fame/?mode=six_seven')
        self.assertEqual(response.status_code, 200)
        entries = list(response.context['entries'])
        self.assertEqual([entry.score for entry in entries], [190, 67, 10])
        self.assertEqual([entry.id for entry in entries], [high.id, middle.id, low.id])
