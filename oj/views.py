from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from .models import Problem, Submission
from .forms import SubmissionForm
from .tasks import judge_submission
import markdown

def problem_list(request):
    problems = Problem.objects.all().order_by('id')
    return render(request, 'oj/problem_list.html', {'problems': problems})

def problem_detail(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)

    # Markdown 渲染
    problem_content = markdown.markdown(
        problem.description,
        extensions=[
            'codehilite',
            'pymdownx.tilde',
            'pymdownx.arithmatex',
            'pymdownx.extra',
            'pymdownx.emoji'
        ]
    )

    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            elapsed = request.POST.get('elapsed_time', -1)
            try:
                elapsed = float(elapsed)
            except (ValueError, TypeError):
                elapsed = -1
            mode = request.POST.get('mode', 'practice')
            if mode == 'practice':
                elapsed = -1

            submission = Submission.objects.create(
                problem=problem,
                language=form.cleaned_data['language'],
                code=form.cleaned_data['code'],
                status='PENDING',
                elapsed_time=elapsed
            )
            judge_submission.delay(submission.id)
            return redirect('submission_detail', sub_id=submission.id)
    else:
        form = SubmissionForm()

    return render(request, 'oj/problem_detail.html', {
        'problem': problem,
        'problem_content': problem_content,
        'form': form
    })


def problem_speedrun(request, problem_id):
    problem = get_object_or_404(Problem, pk=problem_id)

    # Markdown 渲染题目描述
    problem_content = markdown.markdown(
        problem.description,
        extensions=[
            'codehilite',
            'pymdownx.tilde',
            'pymdownx.arithmatex',
            'pymdownx.extra',
            'pymdownx.emoji'
        ]
    )

    if request.method == 'POST':
        form = SubmissionForm(request.POST)
        if form.is_valid():
            elapsed = request.POST.get('elapsed_time', 0)
            try:
                elapsed = float(elapsed)
            except (ValueError, TypeError):
                elapsed = 0

            submission = Submission.objects.create(
                problem=problem,
                language=form.cleaned_data['language'],
                code=form.cleaned_data['code'],
                status='PENDING',
                elapsed_time=elapsed
            )
            judge_submission.delay(submission.id)
            return redirect('submission_detail', sub_id=submission.id)
    else:
        form = SubmissionForm()

    return render(request, 'oj/problem_speedrun.html', {
        'problem': problem,
        'problem_content': problem_content,
        'form': form
    })


def submission_detail(request, sub_id):
    submission = get_object_or_404(Submission, pk=sub_id)
    return render(request, 'oj/submission_detail.html', {'submission': submission})


def submission_status(request, sub_id):
    submission = get_object_or_404(Submission, pk=sub_id)
    data = {
        'status': submission.status,
        'result': submission.result if submission.result else None
    }
    return JsonResponse(data)
