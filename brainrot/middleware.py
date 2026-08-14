from django.conf import settings
from django.http import JsonResponse


class HallOfFameUploadLimitMiddleware:
    """Reject oversized request bodies before Django parses an uploaded file."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method == 'POST' and request.path.rstrip('/') == '/67/submit':
            try:
                content_length = int(request.META.get('CONTENT_LENGTH') or 0)
            except (TypeError, ValueError):
                content_length = 0
            allowance = settings.HOF_MAX_UPLOAD_BYTES + 128 * 1024
            if content_length > allowance:
                return JsonResponse({'error': 'Recording is too large.'}, status=413)
        return self.get_response(request)
