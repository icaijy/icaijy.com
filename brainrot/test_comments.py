import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings

from .comment_markup import render_comment_markdown
from .models import HallOfFameComment, HallOfFameEntry
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

    def test_guest_length_and_rate_limits_are_stricter(self):
        too_long = self.client.post(self.comment_url(), {
            'display_name': 'Guest',
            'body': 'x' * 1001,
        }, REMOTE_ADDR='203.0.113.12')
        self.assertEqual(too_long.status_code, 400)

        for index in range(3):
            response = self.client.post(self.comment_url(), {
                'display_name': 'Guest',
                'body': f'comment {index}',
            }, REMOTE_ADDR='203.0.113.13')
            self.assertEqual(response.status_code, 302)

        blocked = self.client.post(self.comment_url(), {
            'display_name': 'Guest',
            'body': 'fourth',
        }, REMOTE_ADDR='203.0.113.13')
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(HallOfFameComment.objects.filter(author_name='Guest').count(), 3)

    def test_guest_rate_limit_does_not_block_everyone_on_the_same_wifi(self):
        shared_ip = '203.0.113.67'
        for index in range(3):
            response = self.client.post(self.comment_url(), {
                'display_name': 'First Browser',
                'body': f'first {index}',
            }, REMOTE_ADDR=shared_ip)
            self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.post(self.comment_url(), {
            'display_name': 'First Browser',
            'body': 'blocked fourth',
        }, REMOTE_ADDR=shared_ip).status_code, 429)

        second_browser = Client()
        response = second_browser.post(self.comment_url(), {
            'display_name': 'Second Browser',
            'body': 'same school wifi, different browser',
        }, REMOTE_ADDR=shared_ip)
        self.assertEqual(response.status_code, 302)

    def test_logged_in_user_gets_larger_length_limit(self):
        self.client.force_login(self.commenter)
        accepted = self.client.post(self.comment_url(), {'body': 'x' * 1500})
        self.assertEqual(accepted.status_code, 302)
        rejected = self.client.post(self.comment_url(), {'body': 'x' * 4001})
        self.assertEqual(rejected.status_code, 400)

    def test_private_entry_rejects_outsiders_but_owner_can_comment(self):
        self.entry.visibility = HallOfFameEntry.Visibility.PRIVATE
        self.entry.save(update_fields=['visibility'])
        response = self.client.post(self.comment_url(), {
            'display_name': 'Guest',
            'body': 'should not exist',
        }, REMOTE_ADDR='203.0.113.14')
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
