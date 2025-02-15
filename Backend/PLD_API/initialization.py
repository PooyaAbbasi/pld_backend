import os
import django
from django.contrib.auth import get_user_model

# Ensure Django is setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "PLD_API.settings")
django.setup()


def create_superuser():
    """
    Create superuser initially using environment variables.
    """
    User = get_user_model()
    username = os.environ.get('SUPERUSER_USERNAME', 'super_admin')
    password = os.environ.get('SUPERUSER_PASSWORD', 's_u_@')

    # Check if a superuser already exists
    if not User.objects.filter(username=username).exists():
        print("Creating superuser...")
        User.objects.create_superuser(username=username, password=password)
    else:
        print("Superuser already exists.")


if __name__ == "__main__":
    create_superuser()
