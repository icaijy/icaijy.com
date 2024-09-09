from django.shortcuts import redirect
from django.utils.translation import activate
from datetime import datetime, timedelta


def set_language(request):
    user_language = request.POST.get('language', 'en')
    activate(user_language)
    response = redirect(request.POST.get('next', '/'))

    # 设置语言 Cookie（可选）
    expires = datetime.utcnow() + timedelta(days=365)
    response.set_cookie('django_language', user_language, expires=expires, max_age=365 * 24 * 60 * 60)

    return response