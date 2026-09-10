from django.contrib.auth.models import User
from django.db import connection, transaction
from django.utils import timezone


ROLE_MAP = {
    "admin": 1,
    "supervisor": 2,
    "collector": 3,
    "viewer": 4,
}


with transaction.atomic():
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                user_id,
                username,
                full_name,
                role_code,
                phone_number,
                is_active
            FROM app_user
            ORDER BY user_id
        """)
        app_users = cursor.fetchall()

    for user_id, username, full_name, role_code, phone_number, is_active in app_users:
        normalized_username = username.strip().lower()
        normalized_role = str(role_code).strip().lower()

        role_number = ROLE_MAP.get(normalized_role)

        if role_number is None:
            raise ValueError(
                f"Unknown role '{role_code}' for app_user ID {user_id}"
            )

        django_user = User.objects.filter(
            username__iexact=normalized_username
        ).first()

        if django_user is None:
            name_parts = full_name.strip().split(maxsplit=1)

            django_user = User(
                username=normalized_username,
                first_name=name_parts[0],
                last_name=name_parts[1] if len(name_parts) > 1 else "",
                is_active=is_active,
                is_staff=False,
                is_superuser=False,
            )
            django_user.set_unusable_password()
            django_user.save()

            print(f"Created: {normalized_username}")

        else:
            django_user.username = normalized_username
            django_user.is_active = is_active

            # Preserve the separate Django superuser account.
            if not django_user.is_superuser:
                django_user.is_staff = False

            django_user.save()

            print(f"Reused: {normalized_username}")

        with connection.cursor() as cursor:
            cursor.execute("""
                UPDATE app_user
                SET
                    django_user_id = %s,
                    role = %s,
                    email = %s,
                    updated_at = %s
                WHERE user_id = %s
            """, [
                django_user.id,
                role_number,
                django_user.email or None,
                timezone.now(),
                user_id,
            ])

print("User migration completed successfully.")