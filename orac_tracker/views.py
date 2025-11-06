import os
import json
import sys
import subprocess
from django.shortcuts import render, redirect
from django.contrib import messages
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.http import HttpResponse
import platform
from django.utils.translation import gettext as _


MANUAL_DATA = os.path.join(settings.BASE_DIR, 'orac_tracker', 'manual_data.json')
AUTO_DATA = os.path.join(settings.BASE_DIR, 'orac_tracker', 'auto_data.json')
def manual_update():
    from . import scraper
    try:
        scraper.main("manual")
        return
    except subprocess.CalledProcessError:
        return
def index(request):
    manual_update()
    try:
        with open(MANUAL_DATA, 'r') as f:
            manual_data = json.load(f)
    except:
        manual_data = {
            "last_updated": None,
            "data": {
                "overall": {},
                "recent": {
                    "week": {},
                    "month": {},
                    "year": {}
                }
            }
        }

    try:
        with open(AUTO_DATA, 'r') as f:
            auto_data = json.load(f)
    except:
        auto_data = {
            "overall": {},
            "recent": {
                "week": {},
                "month": {},
                "year": {}
            }
        }

    # 合并 overall 数据并计算差值
    overall_data = {}
    for user, manual_solved in manual_data['data']['overall'].items():
        auto_solved = auto_data['overall'].get(user, 0)  # 如果自动数据中没有该用户，默认 0
        diff = manual_solved - auto_solved
        overall_data[_(user)] = {
            'manual': manual_solved,
            'auto': auto_solved,
            'diff': diff
        }

    # 合并 recent 数据并计算差值
    def merge_recent_data(manual_recent, auto_recent):
        merged_recent = {}
        for period in ['week', 'month', 'year']:
            manual_period = manual_recent.get(period, {})
            auto_period = auto_recent.get(period, {})
            merged_recent[period] = {}
            for user, manual_solved in manual_period.items():
                auto_solved = auto_period.get(user, 0)
                diff = manual_solved - auto_solved
                merged_recent[period][_(user)] = {
                    'manual': manual_solved,
                    'auto': auto_solved,
                    'diff': diff
                }
        return merged_recent

    # 合并 manual 和 auto 数据中的 recent 部分
    merged_recent = merge_recent_data(manual_data['data']['recent'], auto_data['recent'])

    # 最终合并 people 数据，包含 overall 和 recent
    people = {
        'overall': overall_data,
        'recent': merged_recent
    }

    return render(request, 'leaderboard/index.html', {
        'people': people,  # 将合并后的数据传递给模板
        'last_updated' : manual_data['last_updated']
    })




