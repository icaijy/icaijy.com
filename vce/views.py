import json
import random
import unicodedata
from datetime import datetime, timedelta

from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from .models import VCEAttempt
from .question_bank import LETTERS, QUESTION_BY_ID, QUESTIONS, TOPIC_LABELS

RUN_SECONDS = 60
PENALTY_SECONDS = 3
SESSION_KEY = "vce_speedrun_v1"


def _json_body(request):
    try:
        value = json.loads(request.body or b"{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _clean_guest_name(raw):
    value = " ".join(str(raw or "").strip().split())
    if not value:
        return "Guest Swan"
    value = value[:32]
    if any(unicodedata.category(ch).startswith("C") for ch in value):
        return "Guest Swan"
    return value


def _public_question(question):
    return {
        "id": question["id"],
        "topic": question["topic"],
        "topic_label": TOPIC_LABELS.get(question["topic"], question["topic"]),
        "stem": question["stem"],
        "options": question["options"],
        "source": question["source"],
    }


def _remaining_ms(state, now=None):
    now = now or timezone.now()
    deadline = datetime.fromtimestamp(
        state["deadline_ts"],
        tz=timezone.get_current_timezone(),
    )
    return max(0, int((deadline - now).total_seconds() * 1000))


def _new_state(display_name):
    order = [question["id"] for question in QUESTIONS]
    random.SystemRandom().shuffle(order)
    now = timezone.now()
    return {
        "started_ts": now.timestamp(),
        "deadline_ts": (now + timedelta(seconds=RUN_SECONDS)).timestamp(),
        "penalty_until_ts": 0.0,
        "display_name": display_name,
        "order": order,
        "index": 0,
        "question_ids": [order[0]],
        "answers": [],
        "score": 0,
        "wrong_count": 0,
    }


def _current_question(state):
    index = state["index"]
    if index >= len(state["order"]):
        refill = [question["id"] for question in QUESTIONS]
        random.SystemRandom().shuffle(refill)
        state["order"].extend(refill)
    return QUESTION_BY_ID[state["order"][state["index"]]]


def _finish_payload(attempt):
    return {
        "finished": True,
        "attempt_id": attempt.pk,
        "score": attempt.score,
        "wrong_count": attempt.wrong_count,
        "review_url": f"/vce/attempt/{attempt.pk}/",
    }


def _persist_finished_run(request, state):
    elapsed_ms = max(
        0,
        min(
            RUN_SECONDS * 1000,
            int((timezone.now().timestamp() - state["started_ts"]) * 1000),
        ),
    )
    with transaction.atomic():
        attempt = VCEAttempt.objects.create(
            user=request.user if request.user.is_authenticated else None,
            display_name="" if request.user.is_authenticated else state["display_name"],
            score=state["score"],
            wrong_count=state["wrong_count"],
            elapsed_ms=elapsed_ms,
            question_ids=state["question_ids"],
            answers=state["answers"],
        )
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True
    return attempt


@ensure_csrf_cookie
def index(request):
    leaders = list(VCEAttempt.objects.select_related("user").all()[:50])
    for rank, attempt in enumerate(leaders, start=1):
        attempt.rank = rank
    personal_best = None
    if request.user.is_authenticated:
        personal_best = (
            VCEAttempt.objects.filter(user=request.user)
            .order_by("-score", "wrong_count", "completed_at")
            .first()
        )
    return render(
        request,
        "vce/index.html",
        {
            "leaders": leaders,
            "question_count": len(QUESTIONS),
            "topic_count": len(TOPIC_LABELS),
            "personal_best": personal_best,
            "run_seconds": RUN_SECONDS,
            "penalty_seconds": PENALTY_SECONDS,
        },
    )


@require_POST
def start_run(request):
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    display_name = "" if request.user.is_authenticated else _clean_guest_name(body.get("display_name"))
    state = _new_state(display_name)
    request.session[SESSION_KEY] = state
    request.session.modified = True
    question = _current_question(state)
    return JsonResponse(
        {
            "ok": True,
            "duration_ms": RUN_SECONDS * 1000,
            "remaining_ms": _remaining_ms(state),
            "question": _public_question(question),
        }
    )


@require_POST
def answer_question(request):
    body = _json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON."}, status=400)
    state = request.session.get(SESSION_KEY)
    if not state:
        return JsonResponse({"error": "No active VCE speedrun."}, status=409)

    now = timezone.now()
    remaining_ms = _remaining_ms(state, now)
    if remaining_ms <= 0:
        attempt = _persist_finished_run(request, state)
        return JsonResponse(_finish_payload(attempt))

    now_ts = now.timestamp()
    penalty_left_ms = max(0, int((state.get("penalty_until_ts", 0.0) - now_ts) * 1000))
    if penalty_left_ms > 0:
        return JsonResponse(
            {
                "error": "Penalty is still active.",
                "penalty_remaining_ms": penalty_left_ms,
                "remaining_ms": remaining_ms,
            },
            status=429,
        )

    question = _current_question(state)
    question_id = str(body.get("question_id") or "")
    choice = str(body.get("choice") or "").upper()
    if question_id != question["id"]:
        return JsonResponse({"error": "Question mismatch. Refresh the run."}, status=409)
    if choice not in LETTERS:
        return JsonResponse({"error": "Choice must be A, B, C or D."}, status=400)

    correct = choice == question["answer"]
    answered_at_ms = max(0, int((now_ts - state["started_ts"]) * 1000))
    state["answers"].append(
        {
            "question_id": question["id"],
            "choice": choice,
            "answer": question["answer"],
            "correct": correct,
            "answered_at_ms": answered_at_ms,
        }
    )
    if correct:
        state["score"] += 1
    else:
        state["wrong_count"] += 1
        state["penalty_until_ts"] = now_ts + PENALTY_SECONDS

    state["index"] += 1
    next_question = _current_question(state)
    state["question_ids"].append(next_question["id"])
    request.session[SESSION_KEY] = state
    request.session.modified = True

    answer_index = LETTERS.index(question["answer"])
    selected_index = LETTERS.index(choice)
    return JsonResponse(
        {
            "finished": False,
            "correct": correct,
            "score": state["score"],
            "wrong_count": state["wrong_count"],
            "remaining_ms": _remaining_ms(state),
            "penalty_ms": PENALTY_SECONDS * 1000 if not correct else 0,
            "correct_answer": question["answer"],
            "correct_option": question["options"][answer_index],
            "explanation": question["explanations"][answer_index],
            "selected_explanation": question["explanations"][selected_index],
            "next_question": _public_question(next_question),
        }
    )


@require_POST
def finish_run(request):
    state = request.session.get(SESSION_KEY)
    if not state:
        return JsonResponse({"error": "No active VCE speedrun."}, status=409)
    remaining_ms = _remaining_ms(state)
    if remaining_ms > 0:
        return JsonResponse(
            {"finished": False, "remaining_ms": remaining_ms},
            status=409,
        )
    attempt = _persist_finished_run(request, state)
    return JsonResponse(_finish_payload(attempt), status=201)


@require_GET
def attempt_detail(request, attempt_id):
    attempt = get_object_or_404(VCEAttempt.objects.select_related("user"), pk=attempt_id)
    answer_map = {item["question_id"]: item for item in attempt.answers}
    questions = []
    for question_id in attempt.question_ids:
        question = QUESTION_BY_ID.get(question_id)
        if not question:
            continue
        answer = answer_map.get(question_id)
        questions.append(
            {
                **_public_question(question),
                "selected": answer["choice"] if answer else None,
                "correct": answer["correct"] if answer else None,
                "correct_answer": question["answer"],
                "explanation": question["explanations"][LETTERS.index(question["answer"])],
            }
        )
    return JsonResponse(
        {
            "id": attempt.pk,
            "player": attempt.public_name,
            "score": attempt.score,
            "wrong_count": attempt.wrong_count,
            "completed_at": attempt.completed_at.isoformat(),
            "questions": questions,
        }
    )
