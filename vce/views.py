import json
import math
import random
import unicodedata
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import AlgorithmicsRun
from .question_bank import ALL_QUESTIONS, BANKS, QUESTION_BY_ID
from brainrot.validators import validate_hall_of_fame_video

GAME_SECONDS = 60
PENALTY_SECONDS = 3
VALID_MODES = {choice for choice, _ in AlgorithmicsRun.GameMode.choices}
PHYSICAL_MODES = VALID_MODES - {AlgorithmicsRun.GameMode.NORMAL}
QUESTION_BATCH_SIZE = 20


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


def _bank_groups():
    groups = []
    for subject in ('Algorithmics (HESS)', 'Chemistry', 'Physics', 'Mathematical Methods', 'Specialist Mathematics'):
        banks = [bank for bank in BANKS.values() if bank.subject == subject]
        if banks:
            groups.append({'subject': subject, 'banks': banks, 'count': sum(len(bank.questions) for bank in banks)})
    return groups


def _finish(run, now=None):
    now = now or timezone.now()
    if run.finished_at is None:
        run.finished_at = min(now, _deadline(run))
        run.save(update_fields=('finished_at',))


def index(request):
    return render(request, 'vce/index.html', {'groups': _bank_groups(), 'chaos': False, 'total_questions': len(ALL_QUESTIONS)})


def chaos_index(request):
    return render(request, 'vce/index.html', {'groups': _bank_groups(), 'chaos': True, 'total_questions': len(ALL_QUESTIONS)})


def play(request, bank_id, chaos=False):
    bank = get_object_or_404_bank(bank_id)
    mode = request.GET.get('mode', AlgorithmicsRun.GameMode.SIX_SEVEN if chaos else AlgorithmicsRun.GameMode.NORMAL)
    allowed_modes = PHYSICAL_MODES if chaos else {AlgorithmicsRun.GameMode.NORMAL}
    if mode not in allowed_modes:
        mode = AlgorithmicsRun.GameMode.SIX_SEVEN if chaos else AlgorithmicsRun.GameMode.NORMAL
    leaders = list(
        AlgorithmicsRun.objects.filter(is_submitted=True, bank_id=bank.id, game_mode=mode)
        .select_related('user')
        .order_by('-final_score', 'finished_at', 'id')[:50]
    )
    return render(request, 'vce/play.html', {
        'leaders': leaders,
        'bank': bank,
        'question_count': len(bank.questions),
        'game_seconds': GAME_SECONDS,
        'penalty_seconds': PENALTY_SECONDS,
        'leaderboard_mode': mode,
        'game_modes': AlgorithmicsRun.GameMode.choices,
        'chaos': chaos,
    })


def chaos_play(request, bank_id):
    return play(request, bank_id, chaos=True)


def get_object_or_404_bank(bank_id):
    bank = BANKS.get(bank_id)
    if bank is None:
        from django.http import Http404
        raise Http404('Question bank not found.')
    return bank


def _new_run(request, bank, game_mode, count=QUESTION_BATCH_SIZE):
    question_ids = [question.id for question in random.sample(bank.questions, min(count, len(bank.questions)))]
    return AlgorithmicsRun.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=_session_key(request),
        question_ids=question_ids,
        game_mode=game_mode,
        bank_id=bank.id,
    )


@require_POST
def prepare_run(request):
    bank = BANKS.get(request.POST.get('bank_id', 'algorithmics_u34'))
    game_mode = request.POST.get('game_mode', AlgorithmicsRun.GameMode.NORMAL)
    if bank is None:
        return JsonResponse({'error': 'Invalid question bank.'}, status=400)
    if game_mode not in VALID_MODES:
        return JsonResponse({'error': 'Invalid game mode.'}, status=400)
    run = _new_run(request, bank, game_mode)
    return JsonResponse({
        'token': str(run.token),
        'questions': [QUESTION_BY_ID[question_id].client_dict() for question_id in run.question_ids],
    }, status=201)


@require_POST
def start_run(request):
    bank = BANKS.get(request.POST.get('bank_id', 'algorithmics_u34'))
    if bank is None:
        return JsonResponse({'error': 'Invalid question bank.'}, status=400)
    game_mode = request.POST.get('game_mode', AlgorithmicsRun.GameMode.NORMAL)
    if game_mode not in VALID_MODES:
        return JsonResponse({'error': 'Invalid game mode.'}, status=400)
    prepared_token = request.POST.get('token')
    if prepared_token:
        with transaction.atomic():
            run = get_object_or_404(AlgorithmicsRun.objects.select_for_update(), token=prepared_token)
            if not _owns(request, run):
                return JsonResponse({'error': 'This run belongs to another session.'}, status=403)
            if run.is_submitted or run.attempts or run.bank_id != bank.id or run.game_mode != game_mode:
                return JsonResponse({'error': 'This prepared run cannot be started.'}, status=409)
            run.started_at = timezone.now()
            run.finished_at = None
            run.locked_until = None
            run.score = 0
            run.save(update_fields=('started_at', 'finished_at', 'locked_until', 'score'))
        return JsonResponse({
            'token': str(run.token), 'started_at': run.started_at.isoformat(),
            'deadline': _deadline(run).isoformat(), 'seconds': GAME_SECONDS,
            'penalty_seconds': PENALTY_SECONDS, 'game_mode': run.game_mode, 'bank_id': run.bank_id,
        })
    run_question_count = min(100, len(bank.questions))
    question_ids = [question.id for question in random.sample(bank.questions, run_question_count)]
    run = AlgorithmicsRun.objects.create(
        user=request.user if request.user.is_authenticated else None,
        session_key=_session_key(request),
        question_ids=question_ids,
        game_mode=game_mode,
        bank_id=bank.id,
    )
    return JsonResponse({
        'token': str(run.token),
        'started_at': run.started_at.isoformat(),
        'deadline': _deadline(run).isoformat(),
        'seconds': GAME_SECONDS,
        'penalty_seconds': PENALTY_SECONDS,
        'position': 0,
        'score': 0,
        'game_mode': run.game_mode,
        'bank_id': run.bank_id,
        'question': _question_at(run, 0).public_dict(),
    }, status=201)


@require_POST
def refill_run(request):
    token = request.POST.get('token', '')
    with transaction.atomic():
        run = get_object_or_404(AlgorithmicsRun.objects.select_for_update(), token=token)
        if not _owns(request, run):
            return JsonResponse({'error': 'This run belongs to another session.'}, status=403)
        if run.is_submitted:
            return JsonResponse({'error': 'This run is already finished.'}, status=409)
        bank = get_object_or_404_bank(run.bank_id)
        used = set(run.question_ids)
        available = [question for question in bank.questions if question.id not in used]
        selected = random.sample(available, min(QUESTION_BATCH_SIZE, len(available)))
        run.question_ids = [*run.question_ids, *(question.id for question in selected)]
        run.save(update_fields=('question_ids',))
    return JsonResponse({'questions': [question.client_dict() for question in selected]})


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
        try:
            metrics = json.loads(request.POST.get('metrics', '{}'))
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({'error': 'Invalid movement data.'}, status=400)
        movement_score, clean_metrics = _movement_result(run.game_mode, metrics)
        if movement_score is None:
            return JsonResponse({'error': 'Invalid movement data.'}, status=400)

        if 'attempts' in request.POST:
            try:
                attempts = json.loads(request.POST['attempts'])
            except (TypeError, ValueError, json.JSONDecodeError):
                return JsonResponse({'error': 'Invalid answer history.'}, status=400)
            clean_attempts = _clean_client_attempts(run, attempts)
            if clean_attempts is None:
                return JsonResponse({'error': 'Invalid answer history.'}, status=400)
            run.attempts = clean_attempts
            run.score = sum(attempt['correct'] is True for attempt in clean_attempts)

        inspected = None
        upload = request.FILES.get('video')
        if upload is not None:
            if run.game_mode == AlgorithmicsRun.GameMode.NORMAL:
                return JsonResponse({'error': 'Video is only accepted for 67 × VCE runs.'}, status=400)
            try:
                inspected = validate_hall_of_fame_video(upload, max_seconds=66)
            except ValidationError as exc:
                return JsonResponse({'error': exc.messages[0]}, status=400)

        run.display_name = '' if request.user.is_authenticated else name
        run.metrics = clean_metrics
        run.movement_score = movement_score
        run.final_score = run.score * movement_score
        run.is_submitted = True
        update_fields = ['display_name', 'metrics', 'movement_score', 'final_score', 'is_submitted']
        if 'attempts' in request.POST:
            update_fields.extend(('attempts', 'score'))
        if inspected:
            run._validated_extension = inspected.extension
            run.video = upload
            run.video_mime_type = inspected.mime_type
            run.video_duration_seconds = inspected.duration_seconds
            update_fields.extend(('video', 'video_mime_type', 'video_duration_seconds'))
        run.save(update_fields=update_fields)
    return JsonResponse({
        'ok': True,
        'score': run.score,
        'movement_score': run.movement_score,
        'final_score': run.final_score,
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
            unanswered = attempt.get('selected') is None
            review = question.review_dict(attempt.get('selected')) | {
                'correct': bool(attempt.get('correct')),
                'unanswered': unanswered,
                'answered_ms': attempt.get('answered_ms', 0),
            }
            review['option_reviews'] = [
                {
                    'letter': chr(65 + index),
                    'text': review['options'][index],
                    'explanation': review['explanations'][index],
                    'is_answer': index == question.answer_index,
                    'is_selected': index == attempt.get('selected'),
                }
                for index, option in enumerate(question.options)
            ]
            reviews.append(review)
    return render(request, 'vce/run_detail.html', {
        'run': run,
        'bank': BANKS.get(run.bank_id),
        'reviews': reviews,
    })


def run_video(request, token):
    run = get_object_or_404(AlgorithmicsRun, token=token, is_submitted=True)
    if not run.video:
        return JsonResponse({'error': 'This legacy run has no recording.'}, status=404)
    extension = 'mp4' if run.video_mime_type == 'video/mp4' else 'webm'
    return FileResponse(
        run.video.open('rb'),
        content_type=run.video_mime_type or 'application/octet-stream',
        as_attachment=request.GET.get('download') == '1',
        filename=f'vce-{run.token}.{extension}',
    )


def _clean_timeline(value):
    if not isinstance(value, list) or len(value) > 1000:
        return None
    clean = []
    previous = -1.0
    for raw in value:
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
            return None
        stamp = round(float(raw), 3)
        if stamp < 0 or stamp > GAME_SECONDS + 1 or stamp < previous:
            return None
        clean.append(stamp)
        previous = stamp
    return clean


def _clean_client_attempts(run, attempts):
    """Validate shape/order only; correctness is intentionally trusted from the client."""
    if not isinstance(attempts, list) or len(attempts) > len(run.question_ids):
        return None
    clean = []
    previous_ms = -1
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict) or attempt.get('question_id') != run.question_ids[index]:
            return None
        selected = attempt.get('selected')
        unanswered = selected is None
        if (not unanswered and (isinstance(selected, bool) or selected not in range(4))) or (unanswered and index != len(attempts) - 1):
            return None
        correct = None if unanswered else attempt.get('correct')
        if not unanswered and not isinstance(correct, bool):
            return None
        answered_ms = attempt.get('answered_ms')
        if isinstance(answered_ms, bool) or not isinstance(answered_ms, int) or not previous_ms <= answered_ms <= (GAME_SECONDS + 1) * 1000:
            return None
        clean.append({'question_id': attempt['question_id'], 'selected': selected, 'correct': correct, 'answered_ms': answered_ms})
        previous_ms = answered_ms
    return clean


def _movement_result(mode, metrics):
    if mode == AlgorithmicsRun.GameMode.NORMAL:
        return 1, {}
    if not isinstance(metrics, dict):
        return None, {}
    if mode == AlgorithmicsRun.GameMode.COMBINE:
        six = _clean_timeline(metrics.get('six_seven'))
        legs = _clean_timeline(metrics.get('leg_claps'))
        if six is None or legs is None:
            return None, {}
        return len(six) * len(legs), {'six_seven': six, 'leg_claps': legs}
    key = 'six_seven' if mode == AlgorithmicsRun.GameMode.SIX_SEVEN else 'leg_claps'
    timeline = _clean_timeline(metrics.get(key))
    if timeline is None:
        return None, {}
    return len(timeline), {key: timeline}
