# oj/tasks.py
from celery import shared_task
from .models import Submission
import tempfile, os, json
from ijudger import judge

@shared_task
def judge_submission(sub_id):
    submission = Submission.objects.get(pk=sub_id)
    problem = submission.problem

    # 读取测试点文件内容
    with problem.test_cases_file.open('rb') as f:
        test_cases_content = f.read().decode('utf-8')

    # 临时写测试点文件
    with tempfile.NamedTemporaryFile('w+', delete=False, suffix='.json') as f:
        f.write(test_cases_content)
        f.flush()
        test_json_path = f.name

    # 临时写代码文件
    ext = 'cpp' if submission.language == 'cpp' else 'py'
    with tempfile.NamedTemporaryFile(suffix=f'.{ext}', mode='w+', delete=False) as f2:
        f2.write(submission.code)
        f2.flush()
        code_path = f2.name

    try:
        results = judge.judge(test_json_path, code_path, submission.language)
        # AC 条件：所有 test case 都 AC
        if all(r['status'] == 'AC' for r in results):
            submission.status = 'AC'
        else:
            submission.status = next(r['status'] for r in results if r['status'] != 'AC')
        submission.result = results
        submission.save()
    finally:
        os.unlink(test_json_path)
        os.unlink(code_path)
