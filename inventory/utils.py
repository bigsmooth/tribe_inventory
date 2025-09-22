# inventory/utils.py
from .models import Hub

def get_visible_hubs(user):
    """
    Superusers (Kevin) see ALL hubs.
    Everyone else sees only their assigned hub (if any).
    Returns a queryset of Hub objects.
    """
    if user.is_superuser:
        return Hub.objects.all()
    if getattr(user, "hub_id", None):
        return Hub.objects.filter(id=user.hub_id)
    # Fallback: no hub assigned → see none
    return Hub.objects.none()
