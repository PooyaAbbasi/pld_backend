from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request
from rest_framework.exceptions import AuthenticationFailed
from django.conf import settings


class AIModelAuthentication(BaseAuthentication):

    def authenticate(self, request: Request):
        token = request.headers.get('x-ai-auth')
        if not token:
            return None

        if token != settings.AI_MODEL_AUTH_TOKEN:
            raise AuthenticationFailed('Invalid token')

        return None, token



