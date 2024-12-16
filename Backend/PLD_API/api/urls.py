from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register('auth/users', UserViewSet)

app_name = 'api'

urlpatterns = [

    path('auth/', include('djoser.urls.jwt')),
] + router.urls
