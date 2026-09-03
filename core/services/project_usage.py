from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
import hashlib

from ..models import (
    ProjectUsage,
    ProjectUsageSettings,
    UserProfile,
)


def get_client_ip(request):
    """
    Get the client's IP address.
    """

    cf_ip = request.META.get("HTTP_CF_CONNECTING_IP")

    if cf_ip:
        return cf_ip.strip()

    return request.META.get("REMOTE_ADDR", "").strip()


def get_identity_key(request):
    """
    Authenticated users:
        user:<user_id>

    Anonymous users:
        anonymous:<hashed_ip>:<session_key>
    """

    if request.user.is_authenticated:
        return f"user:{request.user.pk}"

    if not request.session.session_key:
        request.session.create()

    ip_address = get_client_ip(request)

    ip_hash = hashlib.sha256(
        ip_address.encode("utf-8")
    ).hexdigest()

    return f"anonymous:{ip_hash}:{request.session.session_key}"


def get_daily_limit(request):

    settings_obj = ProjectUsageSettings.objects.first()

    if not settings_obj:
        return 5

    if request.user.is_authenticated:

        profile = getattr(
            request.user,
            "profile",
            None
        )

        if profile and profile.plan == UserProfile.Plan.PAID:
            return settings_obj.paid_daily_limit

    return settings_obj.free_daily_limit


def get_usage(request, project):

    identity_key = get_identity_key(request)
    today = timezone.localdate()

    usage = ProjectUsage.objects.filter(
        identity_key=identity_key,
        project=project,
        date=today
    ).first()

    return usage.count if usage else 0


def check_project_usage(request, project):

    current_usage = get_usage(request, project)
    daily_limit = get_daily_limit(request)

    return current_usage < daily_limit


@transaction.atomic
def consume_project_usage(request, project):
    """
    Consume exactly one usage for the specified project.

    Returns:
        True  -> usage was available and consumed
        False -> daily limit already reached
    """

    identity_key = get_identity_key(request)
    today = timezone.localdate()
    daily_limit = get_daily_limit(request)

    usage, created = (
        ProjectUsage.objects
        .select_for_update()
        .get_or_create(
            identity_key=identity_key,
            project=project,
            date=today,
            defaults={
                "count": 0
            }
        )
    )

    if usage.count >= daily_limit:
        return False

    usage.count += 1

    usage.save(
        update_fields=["count"]
    )

    return True