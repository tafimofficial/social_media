from django.utils import timezone

class UpdateLastActivityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # We use a slight optimization properly: only update if it's been > 1 minute?
            # Or just update every request. For this scale, every request is fine.
            # Ideally we check session, but profile is easier.
            Profile = request.user.profile
            Profile.last_activity = timezone.now()
            Profile.save(update_fields=['last_activity'])

        response = self.get_response(request)
        return response
