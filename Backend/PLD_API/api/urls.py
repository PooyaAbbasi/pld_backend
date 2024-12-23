from django.urls import path, include, re_path
from rest_framework.routers import DefaultRouter

from .views import *
from .models import Automobile

router = DefaultRouter()
router.register('auth/users', UserViewSet)

app_name = 'api'

urlpatterns = [

    path('auth/', include('djoser.urls.jwt')),

    path('automobiles/', AutomobileViewSet.as_view(
        {
            'get': 'list',
            'post': 'create',
        }
    )),

    path('automobiles/all/',
         AutomobileViewSet.as_view(
             {'get': 'list_all'}
         ),
         name='automobiles-list-all'),

    re_path(rf'^automobiles/(?P<plate>{Automobile.PLATE_PATTERN})/$', AutomobileViewSet.as_view(
        {
            'get': 'retrieve',
            'put': 'update',
            'delete': 'destroy',
            'patch': 'partial_update',
        }
    ))


] + router.urls
