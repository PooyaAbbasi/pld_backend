from django.shortcuts import render
from django.shortcuts import get_object_or_404

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.status import (
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND
)

from djoser.views import UserViewSet as DjoserUserViewSet

from .serializers import *
from .models import *


class UserViewSet(DjoserUserViewSet):

    urls_to_exclude = ['set_username', 'reset_username']

    def get_permissions(self):

        if self.action == 'me' and self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        elif self.action in ['retrieve', 'create', 'update', 'partial_update', 'list',]:
            # the 'destroy' action is handled in its action-view.
            return [IsAdminUser()]
        else:
            return super().get_permissions()

    @action(detail=False, methods=['get'], )
    def me(self, request, *args, **kwargs):
        """
            Only provided for get method to show current user details in users/me/ end point
        :return:
        """
        self.get_object = self.get_instance
        if request.method == "GET":
            return self.retrieve(request, *args, **kwargs)

    def destroy(self, request, id):
        """ simple delete view,
            AdminUser permission is needed.
        """

        if not self.request.user.is_staff or not self.request.user.is_superuser:
            # returning 404 instead of 403 is security policy to prevent exposing existence of user with such id.
            return Response(data={'detail': "not found"}, status=HTTP_404_NOT_FOUND)

        user = get_object_or_404(User, id=id)
        user.delete()
        return Response(status=HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'], )
    def set_password(self, request, id, *args, **kwargs):
        """
            set_password endpoint change the password of user with id with new_password in request data
            (only accessible for manager user)
        :return: 204 if successful, 404 if user does not exist,
        """

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_to_update = get_object_or_404(User, id=id)
        user_to_update.set_password(serializer.validated_data['new_password'])
        user_to_update.save()

        return Response(status=HTTP_204_NO_CONTENT)

    # -------------- disable unwanted actions of djoser UserViewSet.

    set_username = None
    reset_username = None
    reset_username_confirm = None
    reset_password = None
    reset_password_confirm = None


@api_view(['GET', 'post'])
def not_found_view(request):
    return Response(data={'Not Found': 'endpoint not found'}, status=HTTP_404_NOT_FOUND)

