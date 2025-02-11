from django.urls import re_path

from .consumers import *

websocket_urlpatterns = [
    re_path(r'ws/traffics/(?P<place_id>\d+)', TrafficConsumer.as_asgi()),
]
