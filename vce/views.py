import random
import unicodedata
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AlgorithmicsRun
from .question_bank import QUESTION_BY_ID, QUESTIONS

GAME_SECONDS = 60
PENALTY_SECONDS = 3
RUN_QUESTION_COUNT = min(100, len(QUESTIONS))


def _session_key(request):
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def _owns(request, run):
    return bool(
        (request.user.is_authenticated and run.user_id == request.user.id)
        or run.session_key == _session_key(request)
    )


def _deadline(run):
    return run.started_at + timedelta(seconds=GAME_SECONDS)


def _question_at(run, position):
    if not 0 <= position < len(run.question_ids):
        return None
    return QUESTION_BY_ID.get(run.question_ids[position])


def _finish(run, now=None):
    now = now or timezone.now()
    if run.finished_at is None:
        run.finished_at = min(now, _deadline(run))
        run.save(update_fields=('finished_at',))


def index(request):
    leaders = list(
        AlgorithmicsRun.objects.filter(is_submitted=True)
        .select_related('user')
        .order_by('-score', 'finished_at', 'id')[:50]
    )
    return render(request, 'vce/index.html', {
        'leaders': leaders,
        'question_count': len(QUESTIONS),
        'game_seconds': GAME_SECONDS,
        'penalty_seconds': PENALTY_SECONDS,
    })


@require_POST
def start_run(request):
    question_ids = [question.id for question in random.sample(QUESTIONS, RUN_QUESTION_COUNT)]
    run = AlgorithmicsRun.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=_session_key(request),
        question_ids=question_ids,
    )
    return JsonResponse({
        'token': str(run.token),
        'started_at': run.started_at.isoformat(),
        'deadline': _deadline(run).isoformat(),
        'seconds': GAME_SECONDS,
        'penalty_seconds': PENALTY_SECONDS,
        'position': 0,
        'score': 0,
        'question': _question_at(run, 0).public_dict(),
    }, status=201)


@require_POST
def answer(request):
    token = request.POST.get('token', '')
    try:
        selected = int(request.POST.get('selected', ''))
        position = int(request.POST.get('position', ''))
    except (TypeError, ValueError):
        return JsonResponse({'error': 'Invalid answer.'}, status=400)
    if selected not in range(4):
        return JsonResponse({'error': 'Invalid answer.'}, status=400)

    with transaction.atomic():
        run = get_object_or_404(AlgorithmicsRun.objects.select_for_update(), token=token)
        if not _owns(request, run):
            return JsonResponse({'error': 'This run belongs to another session.'}, status=403)
        now = timezone.now()
        if run.finished_at or now >= _deadline(run):
            _finish(run, now)
            return JsonResponse({'finished': True, 'score': run.score})
        if run.locked_until and now < run.locked_until:
            wait_ms = max(1, int((run.locked_until - now).total_seconds() * 1000))
            return JsonResponse({'error': 'Penalty active.', 'wait_ms': wait_ms}, status=429)
        if position != len(run.attempts):
            return JsonResponse({'error': 'That question has already been answered.'}, status=409)
        question = _question_at(run, position)
        if question is None:
            _finish(run, now)
            return JsonResponse({'finished': True, 'score': run.score})

        is_correct = selected == question.answer_index
        attempt = {
            'question_id': question.id,
            'selected': selected,
            'correct': is_correct,
            'answered_ms': max(0, int((now - run.started_at).total_seconds() * 1000)),
        }
        run.attempts = [*run.attempts, attempt]
        if is_correct:
            run.score += 1
            run.locked_until = None
        else:
            run.locked_until = now + timedelta(seconds=PENALTY_SECONDS)
        run.save(update_fields=('attempts', 'score', 'locked_until'))

        next_question = _question_at(run, position + 1)
        return JsonResponse({
            'correct': is_correct,
            'score': run.score,
            'position': position + 1,
            'review': question.review_dict(selected),
            'question': next_question.public_dict() if next_question else None,
            'penalty_seconds': PENALTY_SECONDS if not is_correct else 0,
        })


@require_POST
def finish_run(request):
    token = request.POST.get('token', '')
    with transaction.atomic():
        run = get_object_or_404(AlgorithmicsRun.objects.select_for_update(), token=token)
        if not _owns(request, run):
            return JsonResponse({'error': 'This run belongs to another session.'}, status=403)
        now = timezone.now()
        if now < _deadline(run) - timedelta(milliseconds=500):
            return JsonResponse({'error': 'The minute is not over yet.'}, status=409)
        _finish(run, now)

        name = ' '.join(request.POST.get('display_name', '').strip().split())
        if not request.user.is_authenticated:
            if not name:
                name = 'Anonymous Student'
            if len(name) > 32 or any(unicodedata.category(c).startswith('C') for c in name):
                return JsonResponse({'error': 'Display name must be 1–32 ordinary characters.'}, status=400)
            canonical = unicodedata.normalize('NFKC', name).casefold()
            reserved = {'admin', 'administrator', 'moderator', 'staff', 'owner', 'icaijy'}
            registered = {
                unicodedata.normalize('NFKC', username).casefold()
                for username in get_user_model().objects.values_list('username', flat=True)
            }
            if canonical in reserved or canonical in registered:
                return JsonResponse({'error': 'That name belongs to a registered user or site role.'}, status=400)
        run.display_name = '' if request.user.is_authenticated else name
        run.is_submitted = True
        run.save(update_fields=('display_name', 'is_submitted'))
    return JsonResponse({
        'ok': True,
        'score': run.score,
        'detail_url': reverse('vce:run_detail', args=(run.token,)),
    })


def run_detail(request, token):
    run = get_object_or_404(AlgorithmicsRun.objects.select_related('user'), token=token)
    if not run.is_submitted and not _owns(request, run):
        return JsonResponse({'error': 'This run is private.'}, status=404)
    reviews = []
    for attempt in run.attempts:
        question = QUESTION_BY_ID.get(attempt.get('question_id'))
        if question:
            review = question.review_dict(attempt.get('selected')) | {
                'correct': bool(attempt.get('correct')),
                'answered_ms': attempt.get('answered_ms', 0),
            }
            review['option_reviews'] = [
                {
                    'letter': chr(65 + index),
                    'text': option,
                    'explanation': question.explanations[index],
                    'is_answer': index == question.answer_index,
                    'is_selected': index == attempt.get('selected'),
                }
                for index, option in enumerate(question.options)
            ]
            reviews.append(review)
    return render(request, 'vce/run_detail.html', {'run': run, 'reviews': reviews})
