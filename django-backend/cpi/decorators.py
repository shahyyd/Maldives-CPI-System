from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

from .models import AppUser


def role_required(*allowed_roles):
    """
    Allow access only to logged-in users whose AppUser role
    is one of the allowed roles.
    """

    def decorator(view_func):

        @login_required(login_url="supervisor-login")
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            try:
                profile = request.user.cpi_profile
            except AppUser.DoesNotExist:
                messages.error(
                    request,
                    "Your account is not linked to a CPI user profile.",
                )
                return redirect("supervisor-login")

            if not profile.is_active:
                messages.error(
                    request,
                    "Your CPI account has been deactivated.",
                )
                return redirect("supervisor-login")

            if profile.role not in allowed_roles:
                messages.error(
                    request,
                    "You do not have permission to access this page.",
                )
                return redirect("supervisor-dashboard")

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


admin_required = role_required(AppUser.ROLE_ADMIN)

supervisor_required = role_required(
    AppUser.ROLE_ADMIN,
    AppUser.ROLE_SUPERVISOR,
)

viewer_required = role_required(
    AppUser.ROLE_ADMIN,
    AppUser.ROLE_SUPERVISOR,
    AppUser.ROLE_VIEWER,
)