import pickle
from django.shortcuts import render
import os
from django.conf import settings


def analytics(request):
    username = request.GET.get("user", "").strip()

    with open(os.path.join(settings.BASE_DIR, "oracdata", "userData.pkl"), "rb") as f:
        user_data = pickle.load(f)

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

        # 转成 dict: problem -> hof
        def to_dict(lst):
            return {name: val for name, val in lst}

        # 单人
        if len(users) == 1:
            u = users[0]
            solved = sorted(user_data[u], key=lambda x: -x[1])  # 按 hof 排序

            context.update({
                "has_result": True,
                "mode": "single",
                "user": u,
                "solved": solved,
            })

        # 双人
        else:
            u1, u2 = users[:2]

            d1 = to_dict(user_data[u1])
            d2 = to_dict(user_data[u2])

            s1 = set(d1.keys())
            s2 = set(d2.keys())

            both = sorted(
                [(p, d1[p]) for p in s1 & s2],
                key=lambda x: -x[1]
            )

            only1 = sorted(
                [(p, d1[p]) for p in s1 - s2],
                key=lambda x: -x[1]
            )

            only2 = sorted(
                [(p, d2[p]) for p in s2 - s1],
                key=lambda x: -x[1]
            )

            context.update({
                "has_result": True,
                "mode": "dual",
                "u1": u1,
                "u2": u2,
                "both": both,
                "only1": only1,
                "only2": only2,
            })

    return render(request, "analytics.html", context)