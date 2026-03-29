# oj/tasks.py
from .models import Submission
import tempfile, os
from ijudger import judge

def judge_submission(sub_id):
    try:
        submission = Submission.objects.get(pk=sub_id)
        problem = submission.problem

        # 检查测试点文件是否存在
        if not problem.test_cases_file or not problem.test_cases_file.name:
            print(f"[ERROR] Problem {problem.id} 没有测试点文件！")
            submission.status = 'NTF'
            submission.result = [{"status": "NO_TEST_FILE"}]
            submission.save()
            return

        # 检查文件实际存在
        file_path = problem.test_cases_file.path
        if not os.path.exists(file_path):
            print(f"[ERROR] Problem {problem.id} 测试文件不存在: {file_path}")
            submission.status = 'NTF'
            submission.result = [{"status": "NO_TEST_FILE"}]
            submission.save()
            return

        print(f"[INFO] Judging submission {submission.id} for problem {problem.id}")
        print(f"[DEBUG] Test JSON path: {file_path}")

        # 临时写代码文件
        ext = 'cpp' if submission.language == 'cpp' else 'py'
        with tempfile.NamedTemporaryFile(suffix=f'.{ext}', mode='w+', delete=False) as f_code:
            f_code.write(submission.code)
            f_code.flush()
            code_path = f_code.name

        try:
            # 调用 ijudger，传入测试文件绝对路径 + 临时代码文件
            results = judge.judge(file_path, code_path, submission.language)

            # 判题结果处理
            if all(r['status'] == 'AC' for r in results):
                submission.status = 'AC'
            else:
                submission.status = next(r['status'] for r in results if r['status'] != 'AC')
            submission.result = results
            submission.save()

            print(f"[INFO] Submission {submission.id} judged, status: {submission.status}")

        finally:
            # 清理临时代码文件
            os.unlink(code_path)

    except Exception as e:
        print(f"[EXCEPTION] Judging submission {sub_id} failed: {e}")
        try:
            submission = Submission.objects.get(pk=sub_id)
            submission.status = 'UKE'  # Unknown Error
            submission.result = [{"status": "EXCEPTION", "message": str(e)}]
            submission.save()
        except Exception as inner:
            print(f"[FATAL] Could not save error for submission {sub_id}: {inner}")
