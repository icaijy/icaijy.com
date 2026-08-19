import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .comment_markup import render_comment_markdown
from .models import HallOfFameComment, HallOfFameEntry, HallOfFameReaction
from .validators import ValidatedVideo


class CommentMarkdownTests(TestCase):
    def test_markdown_is_rendered_but_untrusted_html_is_sanitized(self):
        rendered = str(render_comment_markdown(
            '**bold** [safe](https://example.com) '
            '<script>alert(1)</script> '
            '[bad](javascript:alert(2))'
        ))
        self.assertIn('<strong>bold</strong>', rendered)
        self.assertIn('https://example.com', rendered)
        self.assertNotIn('<script', rendered.lower())
        self.assertNotIn('alert(1)', rendered)
        self.assertNotIn('javascript:', rendered.lower())

    def test_preview_endpoint_uses_the_same_sanitizer(self):
        response = self.client.post('/67/comments/preview/', {
            'body': '> hello\n\n`67` <img src=x onerror=alert(1)>',
        })
        self.assertEqual(response.status_code, 200)
        html = response.json()['html']
        self.assertIn('<blockquote>', html)
        self.assertIn('<code>67</code>', html)
        self.assertNotIn('<img', html.lower())
        self.assertNotIn('onerror', html.lower())


class HallOfFameCommentTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('owner67', password='owner-password')
        self.commenter = get_user_model().objects.create_user('commenter67', password='comment-password')
        self.other = get_user_model().objects.create_user('other67', password='other-password')
        self.superuser = get_user_model().objects.create_superuser(
            'super67', 'super@example.com', 'super-password'
        )
        self.entry = HallOfFameEntry.objects.create(
            user=self.owner,
            score=67,
            video='hall_of_fame/comment-test.webm',
            mime_type='video/webm',
            duration_seconds=23,
            event_timeline=[1.0, 2.0, 3.0],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

    def comment_url(self):
        return f'/67/hall-of-fame/{self.entry.id}/comments/'

    def test_guest_can_comment_and_is_visibly_labelled(self):
        response = self.client.post(self.comment_url(), {
            'display_name': 'Ruyton Scientist',
            'body': 'actually peak research',
        }, REMOTE_ADDR='203.0.113.10')
        self.assertEqual(response.status_code, 302)
        comment = HallOfFameComment.objects.get()
        self.assertIsNone(comment.user_id)
        self.assertEqual(comment.author_name, 'Ruyton Scientist')
        self.assertTrue(comment.client_key)

        detail = self.client.get(f'/67/hall-of-fame/{self.entry.id}/')
        self.assertContains(detail, 'Ruyton Scientist · guest')
        self.assertContains(detail, 'actually peak research')

    def test_guest_cannot_impersonate_registered_username(self):
        response = self.client.post(self.comment_url(), {
            'display_name': 'commenter67',
            'body': 'totally me bro',
        }, REMOTE_ADDR='203.0.113.11')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(HallOfFameComment.objects.count(), 0)

    def test_guest_length_and_rate_limits_are_doubled(self):
        accepted = self.client.post(self.comment_url(), {
            'display_name': 'Guest',
            'body': 'x' * 1500,
        })
        self.assertEqual(accepted.status_code, 302)

        too_long = Client().post(self.comment_url(), {
            'display_name': 'Guest Too Long',
            'body': 'x' * 2001,
        })
        self.assertEqual(too_long.status_code, 400)

        rate_client = Client()
        for index in range(6):
            response = rate_client.post(self.comment_url(), {
                'display_name': 'Rate Guest',
                'body': f'comment {index}',
            })
            self.assertEqual(response.status_code, 302)
        blocked = rate_client.post(self.comment_url(), {
            'display_name': 'Rate Guest',
            'body': 'seventh',
        })
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(HallOfFameComment.objects.filter(author_name='Rate Guest').count(), 6)

    def test_guest_rate_limit_does_not_block_everyone_on_the_same_wifi(self):
        shared_ip = '203.0.113.67'
        first_browser = Client()
        for index in range(6):
            response = first_browser.post(self.comment_url(), {
                'display_name': 'First Browser',
                'body': f'first {index}',
            }, REMOTE_ADDR=shared_ip)
            self.assertEqual(response.status_code, 302)
        self.assertEqual(first_browser.post(self.comment_url(), {
            'display_name': 'First Browser',
            'body': 'blocked seventh',
        }, REMOTE_ADDR=shared_ip).status_code, 429)

        second_browser = Client()
        response = second_browser.post(self.comment_url(), {
            'display_name': 'Second Browser',
            'body': 'same school wifi, different browser',
        }, REMOTE_ADDR=shared_ip)
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_gets_doubled_length_limit(self):
        self.client.force_login(self.commenter)
        accepted = self.client.post(self.comment_url(), {'body': 'x' * 6000})
        self.assertEqual(accepted.status_code, 302)
        rejected = self.client.post(self.comment_url(), {'body': 'x' * 8001})
        self.assertEqual(rejected.status_code, 400)

    def test_logged_in_user_gets_forty_comments_per_window(self):
        self.client.force_login(self.commenter)
        for index in range(40):
            response = self.client.post(self.comment_url(), {'body': f'auth comment {index}'})
            self.assertEqual(response.status_code, 302)
        blocked = self.client.post(self.comment_url(), {'body': 'forty first'})
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(HallOfFameComment.objects.filter(user=self.commenter).count(), 40)

    def test_private_entry_rejects_outsiders_but_owner_can_comment(self):
        self.entry.visibility = HallOfFameEntry.Visibility.PRIVATE
        self.entry.save(update_fields=['visibility'])
        response = self.client.post(self.comment_url(), {
            'display_name': 'Guest',
            'body': 'should not exist',
        })
        self.assertEqual(response.status_code, 404)

        self.client.force_login(self.owner)
        response = self.client.post(self.comment_url(), {'body': 'owner note'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(HallOfFameComment.objects.count(), 1)

    def test_owner_comment_is_marked_op_and_leaderboard_counts_comments(self):
        comment = HallOfFameComment.objects.create(
            entry=self.entry,
            user=self.owner,
            author_name=self.owner.username,
            body='my technique is classified',
        )
        detail = self.client.get(f'/67/hall-of-fame/{self.entry.id}/')
        self.assertContains(detail, 'my technique is classified')
        self.assertContains(detail, '>OP<')
        self.assertContains(detail, f'id="comment-{comment.id}"')

        board = self.client.get('/67/hall-of-fame/')
        board_entry = list(board.context['entries'])[0]
        self.assertEqual(board_entry.comment_count, 1)
        self.assertContains(board, f'/67/hall-of-fame/{self.entry.id}/#comments')

    def test_comment_delete_permissions(self):
        comment = HallOfFameComment.objects.create(
            entry=self.entry,
            user=self.commenter,
            author_name=self.commenter.username,
            body='delete permissions test',
        )
        delete_url = f'/67/comments/{comment.id}/delete/'

        self.client.force_login(self.other)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.assertTrue(HallOfFameComment.objects.filter(pk=comment.pk).exists())

        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(delete_url).status_code, 302)
        self.assertFalse(HallOfFameComment.objects.filter(pk=comment.pk).exists())

        second = HallOfFameComment.objects.create(
            entry=self.entry,
            user=self.commenter,
            author_name=self.commenter.username,
            body='self delete',
        )
        self.client.force_login(self.commenter)
        self.assertEqual(self.client.post(f'/67/comments/{second.id}/delete/').status_code, 302)
        self.assertFalse(HallOfFameComment.objects.filter(pk=second.pk).exists())

        third = HallOfFameComment.objects.create(
            entry=self.entry,
            user=self.other,
            author_name=self.other.username,
            body='admin delete',
        )
        self.client.force_login(self.superuser)
        self.assertEqual(self.client.post(f'/67/comments/{third.id}/delete/').status_code, 302)
        self.assertFalse(HallOfFameComment.objects.filter(pk=third.pk).exists())


class HallOfFameReactionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('reactowner', password='x')
        self.entry = HallOfFameEntry.objects.create(
            user=self.owner,
            score=100,
            video='hall_of_fame/reaction.webm',
            mime_type='video/webm',
            duration_seconds=23,
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        self.comment = HallOfFameComment.objects.create(
            entry=self.entry,
            user=self.owner,
            author_name=self.owner.username,
            body='peak',
        )

    def toggle(self, client, target_type, target_id, emoji='😋'):
        return client.post('/67/reactions/toggle/', {
            'target_type': target_type,
            'target_id': target_id,
            'emoji': emoji,
        })

    def test_guest_can_toggle_run_reaction_without_login(self):
        response = self.toggle(self.client, 'entry', self.entry.id)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['active'])
        reaction = HallOfFameReaction.objects.get()
        self.assertIsNone(reaction.user_id)
        self.assertTrue(reaction.reactor_key.startswith('g:'))

        response = self.toggle(self.client, 'entry', self.entry.id)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()['active'])
        self.assertEqual(HallOfFameReaction.objects.count(), 0)

    def test_two_guest_browsers_have_independent_reaction_identity(self):
        other_browser = Client()
        self.toggle(self.client, 'entry', self.entry.id, '🔥')
        self.toggle(other_browser, 'entry', self.entry.id, '🔥')
        self.assertEqual(HallOfFameReaction.objects.filter(emoji='🔥').count(), 2)

    def test_guest_can_react_to_comment_and_multiple_emoji(self):
        self.assertEqual(self.toggle(self.client, 'comment', self.comment.id, '😂').status_code, 200)
        self.assertEqual(self.toggle(self.client, 'comment', self.comment.id, '💀').status_code, 200)
        self.assertEqual(HallOfFameReaction.objects.filter(comment=self.comment).count(), 2)

    def test_logged_in_reaction_is_account_bound(self):
        self.client.force_login(self.owner)
        self.toggle(self.client, 'entry', self.entry.id, '😋')
        reaction = HallOfFameReaction.objects.get()
        self.assertEqual(reaction.user, self.owner)
        self.assertEqual(reaction.reactor_key, f'u:{self.owner.id}')


class PersonalBestAndAnalysisTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('pbuser', password='x')
        self.old = HallOfFameEntry.objects.create(
            user=self.user,
            game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
            score=120,
            video='hall_of_fame/pb-old.webm',
            mime_type='video/webm',
            duration_seconds=23,
            event_timeline=[],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )
        self.pb = HallOfFameEntry.objects.create(
            user=self.user,
            game_mode=HallOfFameEntry.GameMode.SIX_SEVEN,
            score=150,
            video='hall_of_fame/pb.webm',
            mime_type='video/webm',
            duration_seconds=23,
            event_timeline=[round((index + 1) * 20 / 151, 3) for index in range(150)],
            visibility=HallOfFameEntry.Visibility.PUBLIC,
        )

    def test_hof_list_exposes_registered_user_pb(self):
        response = self.client.get('/67/hall-of-fame/?mode=six_seven')
        entries = list(response.context['entries'])
        by_id = {entry.id: entry for entry in entries}
        self.assertEqual(by_id[self.old.id].personal_best, 150)
        self.assertFalse(by_id[self.old.id].is_personal_best)
        self.assertTrue(by_id[self.pb.id].is_personal_best)
        self.assertContains(response, 'PB 150')

    def test_detail_shows_pb_and_exact_speed_analysis(self):
        response = self.client.get(f'/67/hall-of-fame/{self.pb.id}/')
        self.assertContains(response, 'Best 150')
        self.assertContains(response, 'run-speed-analysis')
        self.assertContains(response, 'run-event-timeline')

    def test_legacy_run_does_not_fake_speed_curve(self):
        response = self.client.get(f'/67/hall-of-fame/{self.old.id}/')
        self.assertNotContains(response, 'id="run-speed-analysis"')
        self.assertContains(response, 'fake science')


class SubmissionCommentTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.override = override_settings(
            PRIVATE_MEDIA_ROOT=self.media.name,
            TURNSTILE_ENABLED=False,
        )
        self.override.enable()
        self.user = get_user_model().objects.create_user('runner67', password='runner-password')
        self.client.force_login(self.user)

    def tearDown(self):
        self.override.disable()
        self.media.cleanup()

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_video_submission_can_create_first_op_comment(self, validate_video):
        validate_video.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        video = SimpleUploadedFile('run.webm', b'fake validated video', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'game_mode': HallOfFameEntry.GameMode.SIX_SEVEN,
            'score': '67',
            'publication_consent': 'yes',
            'submission_comment': '**new PB** somehow',
            'video': video,
        })
        self.assertEqual(response.status_code, 201)
        entry = HallOfFameEntry.objects.get(user=self.user)
        comment = HallOfFameComment.objects.get(entry=entry)
        self.assertTrue(comment.is_submission_note)
        self.assertEqual(comment.user, self.user)
        self.assertEqual(comment.body, '**new PB** somehow')

        detail = self.client.get(f'/67/hall-of-fame/{entry.id}/')
        self.assertContains(detail, '<strong>new PB</strong> somehow')
        self.assertContains(detail, 'submission note')
        self.assertContains(detail, '>OP<')

    @patch('brainrot.views.validate_hall_of_fame_video')
    def test_submission_comment_is_optional(self, validate_video):
        validate_video.return_value = ValidatedVideo('video/webm', 'webm', 23.0)
        video = SimpleUploadedFile('run.webm', b'fake validated video', content_type='video/webm')
        response = self.client.post('/67/submit/', {
            'game_mode': HallOfFameEntry.GameMode.SIX_SEVEN,
            'score': '1',
            'publication_consent': 'yes',
            'video': video,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(HallOfFameComment.objects.count(), 0)
