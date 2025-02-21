from urllib.parse import parse_qs
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth import get_user_model

User = get_user_model()


@database_sync_to_async  # using channels decorator to make database operation async.
def get_user(user_id):
    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
        Middleware to authenticate JWT token
    """
    async def __call__(self, scope, receive, send):
        """
        Authenticate user with JWT token provided in url query string,
        and set the user in `scope`, else an AnonymousUser is set.
        :returns: super method at the end.
        """
        query_string = parse_qs(scope["query_string"].decode())

        token = query_string.get("token", [None])[0]  # Extract token from URL query parameters
        scope["user"] = AnonymousUser()

        if token:
            try:
                decoded_token = AccessToken(token)  # Decode JWT
                user = await get_user(decoded_token["user_id"])
                scope["user"] = user  # Attach user to scope
            except Exception as e:
                print(f"authentication failed: {e}")

        return await super().__call__(scope, receive, send)


