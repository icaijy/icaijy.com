import pickle
from django.shortcuts import render

def analytics(request):
    username = request.GET.get("user", "").strip()

    with open("data.pkl", "rb") as f:
        user_data = pickle.load(f)

    # 你需要自己准备 problem_data（比如从另一个 pkl 或 json）
    with open("problem_stats.pkl", "rb") as f:
        problem_data = pickle.load(f)

    context = {
        "has_result": False
    }

    if username:
        users = [u.strip() for u in username.split(",") if u.strip()]

        # 检查用户存在
        for u in users:
            if u not in user_data:
                context["error"] = f'User "{u}" not found'
                return render(request, "analytics.html", context)

        all_pids = list(problem_data.keys())

        def getP(pid):
            p = problem_data[pid]
            return {"pid": pid, **p}

        # 单人
        if len(users) == 1:
            u = users[0]
            solved = user_data[u]
            solved_pids = set(p[0] for p in solved)

            unsolved = [getP(p) for p in all_pids if p not in solved_pids]

            context.update({
                "has_result": True,
                "mode": "single",
                "user": u,
                "solved": solved,
                "unsolved": unsolved
            })

        # 双人
        else:
            u1, u2 = users[:2]

            s1 = set(p[0] for p in user_data[u1])
            s2 = set(p[0] for p in user_data[u2])

            both = list(s1 & s2)
            only1 = list(s1 - s2)
            only2 = list(s2 - s1)
            neither = [p for p in all_pids if p not in s1 and p not in s2]

            context.update({
                "has_result": True,
                "mode": "dual",
                "u1": u1,
                "u2": u2,
                "both": both,
                "only1": only1,
                "only2": only2,
                "neither": neither,
            })

    return render(request, "analytics.html", context)