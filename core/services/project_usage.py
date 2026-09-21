from django.db import transaction
from django.utils import timezone
import hashlib

from ..models import (
    SaaSProduct,
    SaaSSubscription,
    SaaSUsage,
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


def get_active_subscription(user, product):
    """
    Return the user's active subscription for
    the specified SaaS product.

    Returns:
        SaaSSubscription | None
    """

    if not user.is_authenticated:
        return None

    subscription = (
        SaaSSubscription.objects
        .filter(
            user=user,
            product=product,
            status=SaaSSubscription.Status.ACTIVE,
        )
        .order_by("-created_at")
        .first()
    )

    if not subscription:
        return None

    if not subscription.is_active:
        return None

    return subscription


def get_daily_limit(request, product):
    """
    Determine the daily limit for a user.

    Anonymous:
        SaaSProduct.free_daily_limit

    Authenticated free:
        SaaSProduct.free_daily_limit

    Authenticated paid:
        Active subscription.daily_limit
    """

    subscription = get_active_subscription(
        request.user,
        product
    )

    if subscription:
        return subscription.daily_limit

    return product.free_daily_limit


def get_usage(request, product):
    """
    Return today's usage for the specified SaaS product.
    """

    today = timezone.localdate()

    if request.user.is_authenticated:
        usage = (
            SaaSUsage.objects
            .filter(
                user=request.user,
                product=product,
                date=today,
            )
            .first()
        )
    else:
        identity_key = get_identity_key(request)

        usage = (
            SaaSUsage.objects
            .filter(
                user__isnull=True,
                identity_key=identity_key,
                product=product,
                date=today,
            )
            .first()
        )

    return usage.count if usage else 0


def check_project_usage(request, product):
    """
    Check whether another operation is allowed.

    Returns:
        True  -> usage available
        False -> daily limit reached
    """

    current_usage = get_usage(
        request,
        product
    )

    daily_limit = get_daily_limit(
        request,
        product
    )

    return current_usage < daily_limit


@transaction.atomic
def consume_project_usage(request, product):
    """
    Consume exactly one usage for the specified
    SaaS product.

    Returns:
        True  -> usage was available and consumed
        False -> daily limit already reached
    """

    today = timezone.localdate()

    daily_limit = get_daily_limit(
        request,
        product
    )

    if request.user.is_authenticated:

        usage, created = (
            SaaSUsage.objects
            .select_for_update()
            .get_or_create(
                user=request.user,
                product=product,
                date=today,
                defaults={
                    "identity_key": "",
                    "count": 0,
                },
            )
        )

    else:

        identity_key = get_identity_key(request)

        usage, created = (
            SaaSUsage.objects
            .select_for_update()
            .get_or_create(
                user=None,
                identity_key=identity_key,
                product=product,
                date=today,
                defaults={
                    "count": 0,
                },
            )
        )

    if usage.count >= daily_limit:
        return False

    usage.count += 1

    usage.save(
        update_fields=["count"]
    )

    return True