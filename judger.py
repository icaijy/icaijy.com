import os
import sys
import django
import time

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myblog.settings")
django.setup()

from oj.models import Submission
from oj.tasks import judge_submission

def run_judger():
    print("[INFO] Judger started...")
    while True:
        try:
            # 取最早的 PENDING 提交
            sub = Submission.objects.filter(status='PENDING').order_by('submit_time').first()
            if sub:
                print(f"[INFO] Judging submission {sub.id} for problem {sub.problem.id}")
                judge_submission(sub.id)
            else:
                time.sleep(1)
        except Exception as e:
            print(f"[EXCEPTION] Judger loop failed: {e}")
            time.sleep(1)

if __name__ == "__main__":
    run_judger()
