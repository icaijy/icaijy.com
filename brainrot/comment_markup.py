import markdown
import nh3
from django.core.exceptions import ValidationError
from django.utils.safestring import mark_safe

ANONYMOUS_COMMENT_MAX_LENGTH = 2000
AUTHENTICATED_COMMENT_MAX_LENGTH = 8000

_ALLOWED_TAGS = {
    'p', 'br', 'strong', 'em', 'del', 'code', 'pre', 'blockquote',
    'ul', 'ol', 'li', 'a', 'hr',
}
_ALLOWED_ATTRIBUTES = {
    'a': {'href', 'title'},
}
_ALLOWED_URL_SCHEMES = {'http', 'https', 'mailto'}


def comment_max_length(user):
    return AUTHENTICATED_COMMENT_MAX_LENGTH if getattr(user, 'is_authenticated', False) else ANONYMOUS_COMMENT_MAX_LENGTH


def normalise_comment_body(raw_body, user=None, *, allow_blank=False):
    body = (raw_body or '').strip()
    if not body and allow_blank:
        return ''
    if not body:
        raise ValidationError('Write something before posting your comment.')

    limit = comment_max_length(user)
    if len(body) > limit:
        raise ValidationError(f'Comment is too long. The limit is {limit} characters.')
    return body


def render_comment_markdown(body):
    """Render a deliberately small Markdown dialect and sanitize the result.

    Blog posts are trusted author content; HOF comments are not. Raw HTML may be
    present in Markdown input, so every rendered comment passes through nh3
    before Django is told the HTML is safe.
    """
    rendered = markdown.markdown(
        body or '',
        extensions=['sane_lists', 'nl2br', 'pymdownx.tilde'],
        output_format='html5',
    )
    cleaned = nh3.clean(
        rendered,
        tags=_ALLOWED_TAGS,
        clean_content_tags={'script', 'style'},
        attributes=_ALLOWED_ATTRIBUTES,
        url_schemes=_ALLOWED_URL_SCHEMES,
        url_relative='pass_through',
        link_rel='nofollow noopener noreferrer',
    )
    return mark_safe(cleaned)
