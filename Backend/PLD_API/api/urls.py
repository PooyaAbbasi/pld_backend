from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register('auth/users', UserViewSet)

urlpatterns = [
    # path('auth/jwt/create/', CustomTokenObtainPairView.as_view()),
    # path('auth', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
] + router.urls
