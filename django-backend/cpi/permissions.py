from rest_framework.permissions import BasePermission

from .models import AppUser


class IsAdministrator(BasePermission):
    """
    Allows access only to CPI Administrators.
    """

    message = "Only Administrators can perform this action."

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False

        try:
            return (
                request.user.cpi_profile.is_active and
                request.user.cpi_profile.role == AppUser.ROLE_ADMIN
            )
        except AppUser.DoesNotExist:
            return False