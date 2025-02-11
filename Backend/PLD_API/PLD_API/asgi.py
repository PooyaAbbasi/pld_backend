"""
ASGI config for PLD_API project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from api.middlewares import JWTAuthMiddleware
from api.routing import websocket_urlpatterns


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PLD_API.settings')

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        'http': django_asgi_app,
        "websocket": JWTAuthMiddleware(  # applying simple-jwt authentication custom middleware
            AuthMiddlewareStack(
                URLRouter(websocket_urlpatterns)
            )
        ),

    }
)


