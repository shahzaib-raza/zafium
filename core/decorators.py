from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect

from .services.project_usage import consume_project_usage


def project_usage_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not consume_project_usage(request):

            messages.warning(
                request,
                "You have reached your daily project usage limit. "
                "Please try again tomorrow or upgrade your account."
            )

            return redirect("core:projects")

        return view_func(
            request,
            *args,
            **kwargs
        )

    return wrapper