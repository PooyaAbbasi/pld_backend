from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings
from .models import User


class AIModelAuthentication(BaseAuthentication):
    """
        Simple authentication with provided header by AI_Model service.
    """

    def authenticate(self, request: Request):
        """
        :return: If token in `x-ai-auth` headers is provided, and it is equal to determined token value in settings
            a sample user will be returned. else None.
        """
        token = request.headers.get('x-ai-auth')
        if not token:
            return None, token

        if token != settings.AI_MODEL_AUTH_TOKEN:
            return None, token

        user = User.objects.first()
        return user, token



