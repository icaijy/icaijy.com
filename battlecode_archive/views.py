"""Read-only public archive; no bot execution, no public upload endpoint."""
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.core.paginator import Paginator
from django.views.decorators.http import require_GET
from django.views.decorators.clickjacking import xframe_options_exempt
from .models import BattleSeason, BattleMatch


def index(request):
    return render(request, 'battlecode_archive/index.html', {
        'seasons': BattleSeason.objects.filter(is_public=True)})


def detail(request, slug):
    season = get_object_or_404(BattleSeason, slug=slug, is_public=True)
    page = Paginator(season.matches.all(), 40).get_page(request.GET.get('page'))
    return render(request, 'battlecode_archive/detail.html', {'season':season,'page':page})


def match_detail(request, slug, index):
    season = get_object_or_404(BattleSeason, slug=slug, is_public=True)
    match = get_object_or_404(BattleMatch, season=season, index=index)
    return render(request, 'battlecode_archive/match.html', {'season':season,'match':match})


@xframe_options_exempt
@require_GET
def viewer(request, slug):
    season = get_object_or_404(BattleSeason, slug=slug, is_public=True)
    response = HttpResponse(season.viewer_html, content_type='text/html; charset=utf-8')
    # Untrusted season-specific HTML is stored in the DB; enforce opaque origin,
    # no network and no access to the parent page's cookies or DOM.
    response['Content-Security-Policy'] = (
        "sandbox allow-scripts; default-src 'none'; "
        "script-src 'unsafe-inline'; style-src 'unsafe-inline'; "
        "img-src data: blob:; font-src data:; connect-src 'none'; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'self'")
    response['Cache-Control'] = 'public, max-age=300'
    return response


@require_GET
def replay(request, slug, index):
    season = get_object_or_404(BattleSeason, slug=slug, is_public=True)
    match = get_object_or_404(BattleMatch, season=season, index=index)
    response = JsonResponse(match.replay)
    response['Cache-Control'] = 'public, max-age=300'
    return response
