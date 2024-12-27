from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch

from rest_framework import viewsets
from rest_framework.mixins import (
    CreateModelMixin,
    UpdateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.status import *
from rest_framework.pagination import PageNumberPagination

from djoser.views import UserViewSet as DjoserUserViewSet

from .serializers import *
from .models import *
from .permissions import IsManagerUser


class UserViewSet(DjoserUserViewSet):

    urls_to_exclude = ['set_username', 'reset_username']

    def get_permissions(self):

        if self.action == 'me' and self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        elif self.action in ['retrieve', 'create', 'update', 'partial_update', 'list', 'destroy']:
            return [IsManagerUser()]
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

        if not self.request.user.is_manager:
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


class AutomobileViewSet(viewsets.ModelViewSet):

    pagination_class = PageNumberPagination

    lookup_field = 'plate'

    @action(detail=False, methods=['get'], url_path='all', url_name='list-all')
    def list_all(self, request, *args, **kwargs):
        """
        :return: all automobiles anonymous or non-anonymous objs.
        """
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def update(self, request, *args, **kwargs):
        response = super().update(request, *args, **kwargs)

        return self.__response_with_refreshed_data_if_ok(response)

    @action(detail=True, methods=['get'], )
    def permissions(self, request, plate, *args, **kwargs):
        related_permissions = TemporaryPermission.objects.filter(automobile_id=plate).all()
        filtered_queryset = self.filter_queryset(related_permissions)

        page = self.paginate_queryset(filtered_queryset)
        if page is not None:
            serializer = TemporaryPermissionSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = TemporaryPermissionSerializer(related_permissions, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def get_queryset(self):

        # annotate the query set with is_permitted_conditions of Automobile model, as `is_permitted`.
        query_set = Automobile.get_annotated_is_permitted(Automobile.objects.all())

        for auto in query_set:
            print(repr(auto))

        match self.action:
            case 'list_all':
                return query_set

            case 'list':
                # returns all registered automobiles which doesn't satisfy anonymous conditions
                registered_automobiles = (query_set.filter(~Automobile.is_anonymous_conditions()).distinct())
                return registered_automobiles

            case 'retrieve':
                return Automobile.objects.all()
            case _:  # other actions
                return query_set

    def get_permissions(self):

        if self.action in ('retrieve', 'permissions'):
            # ordinary users only have permission to read detail of automobile
            return [IsAuthenticated()]
        else:
            return [IsManagerUser()]

    def __response_with_refreshed_data_if_ok(self, response: Response):
        """
        :param response: response that was made.
        :return: if status of response is 200_ok, with refreshed data of instance
            to ensure that data contains all changes confirmed in database
            else return response without change.
        """
        if response.status_code == HTTP_200_OK:
            # Re-Fetch instance data from database.
            refreshed_instance = self.get_object()
            response.data = self.get_serializer(refreshed_instance).data

        return response

    def get_serializer_class(self, *args, **kwargs):
        if self.action in ['partial_update', 'update']:
            return AutomobileUpdateSerializer
        elif self.action == 'retrieve':
            return AutomobileDetailSerializer
        else:
            return AutomobileSerializer


class TemporaryPermissionViewSet(
    CreateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
    viewsets.GenericViewSet
):

    queryset = TemporaryPermission.objects.all().select_related('automobile')
    serializer_class = TemporaryPermissionSerializer

    pagination_class = PageNumberPagination

    def partial_update(self, request, *args, **kwargs):

        instance: TemporaryPermission = self.get_object()
        data = request.data
        serializer = ModifyTempPermissionSerializer(
            instance,
            data=data,
            partial=True,
            context=self.get_serializer_context()
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(data=serializer.data, status=HTTP_200_OK)

    def get_permissions(self):
        if self.action in ('create', 'retrieve'):
            return [IsAuthenticated()]
        else:
            return [IsManagerUser()]
