from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.db.models import Prefetch

from rest_framework import viewsets
from rest_framework.mixins import (
    CreateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
    RetrieveModelMixin, UpdateModelMixin,
)
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS, AllowAny
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.status import *
from rest_framework.pagination import PageNumberPagination
from rest_framework.filters import SearchFilter
from rest_framework.generics import ListAPIView, ListCreateAPIView


from djoser.views import UserViewSet as DjoserUserViewSet
from django_filters.rest_framework import DjangoFilterBackend

from .serializers import *
from .models import *
from .permissions import IsManagerUser
from .filters import *
from .authenticators import *
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

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def logout(self, request: Request):

        if not request.user.is_manager:
            place_id = request.COOKIES.get('place_id')
            if not place_id:
                return Response(
                    data={
                        'message': 'place_id is required',
                    },
                    status=HTTP_400_BAD_REQUEST
                )

            place = get_object_or_404(Place, id=place_id)

            data = {"message": "با موفقیت خارج شدید"}
            if not place.is_assigned:
                # only include some message in response and let security agent log out.
                data = {'message': 'این مکان تنظیم نشده است، باید توسط مدیریت تنظیم شود'},

            try:
                SecurityAssignment.remove_security_agent(agent=request.user, place=place)
                return Response(data=data, status=HTTP_200_OK)
            except ValidationError as e:
                return Response(data={'message': str(e)}, status=HTTP_400_BAD_REQUEST)

        return Response(data={"message": "با موفقیت خارج شدید"}, status=HTTP_200_OK)


@api_view(['GET', 'post'])
def not_found_view(request):
    return Response(data={'Not Found': 'endpoint not found'}, status=HTTP_404_NOT_FOUND)


class AutomobileViewSet(viewsets.ModelViewSet):

    pagination_class = PageNumberPagination
    lookup_field = 'plate'

    filter_backends = [SearchFilter, ]
    search_fields = ['plate', 'owner_username']

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
        related_permissions = TemporaryPermission.objects.filter(automobile_id=plate).order_by('-to_time')

        serializer = TemporaryPermissionSerializer(related_permissions, many=True)
        return Response(serializer.data, status=HTTP_200_OK)

    def get_queryset(self):

        # annotate the query set with is_permitted_conditions of Automobile model, as `is_permitted`.
        query_set = Automobile.get_annotated_is_permitted(Automobile.objects.all())

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

        if self.action in ('retrieve',):
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
    RetrieveModelMixin,
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

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TempPermissionDetailSerializer
        else:
            return TemporaryPermissionSerializer


class PlaceViewSet(
    CreateModelMixin,
    ListModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
    viewsets.GenericViewSet
):

    queryset = Place.objects.prefetch_related('gates')
    serializer_class = PlaceSerializer
    permission_classes = [IsManagerUser,]

    @action(detail=False, methods=['post'])
    def set_place(self, request, *args, **kwargs):
        place_id = self.request.data.get('place_id')
        if not place_id:
            return Response({'message': 'place_id is required'}, status=HTTP_400_BAD_REQUEST)

        # check client place is sat before or not.
        try:
            self.check_current_place()
        except ValidationError as e:
            return Response({'message': f'{e.detail}'}, status=HTTP_400_BAD_REQUEST)

        place = get_object_or_404(Place, id=place_id)
        try:
            # check target place is sat for other client before or not.
            self.set_place_assigned(place)
        except ValidationError as e:
            return Response({'message': f'{e.detail}'}, status=HTTP_400_BAD_REQUEST)

        # set place_id in cookies for this client
        response = Response(data={"message": f"مکان "
                                             f"{place.name}"
                                             f" برای این سیستم با موفقیت ثبت شد"},
                            status=HTTP_200_OK)

        one_year_in_seconds = 60 * 60 * 24 * 365
        response.set_cookie(
            key='place_id',
            value=place_id,
            httponly=True,
            max_age=one_year_in_seconds,
            samesite='Strict',
            path='/api/',
            domain=settings.DOMAIN,
        )

        return response

    def check_current_place(self):
        # check client place is sat before or not.
        current_place_id = self.request.COOKIES.get('place_id')
        if current_place_id is not None:
            if Place.objects.filter(id=current_place_id, is_assigned=True).exists():
                raise ValidationError('مکان دیگری هم اکنون برای این سیستم ثبت شده')

    def set_place_assigned(self, place: Place):
        if place.is_assigned:
            raise ValidationError('این مکان پیش از این برای این سیستم یا سیستم دیگری ثبت شده'
                                  ' ابتدا باید آنرا آزاد کنید یا همه مکان ها را بازنشانی کنید')

        place.is_assigned = True
        place.save()

    @action(detail=False, methods=['post'])
    def remove_place(self, request, *args, **kwargs):
        place_id = self.request.COOKIES.get('place_id')
        if place_id is not None:
            place = get_object_or_404(Place, id=place_id)
            place.is_assigned = False
            place.save()

        response = Response(data={'message': "مکان  سیستم با موفقیت حذف شد"}, status=HTTP_200_OK)
        response.delete_cookie(
            key='place_id',
            path='/api/',
            domain=settings.DOMAIN,
            samesite='Strict',
        )
        return response

    @action(detail=False, methods=['post'])
    def reset_all_places(self, request, *args, **kwargs):
        Place.reset_assigned()
        return Response(data={'message': "مکان ها با موفقیت بازنشانی شدند"}, status=HTTP_200_OK)


class GateViewSet(
    CreateModelMixin,
    DestroyModelMixin,
    UpdateModelMixin,
    viewsets.GenericViewSet
):
    queryset = Gate.objects.all()
    permission_classes = [IsManagerUser,]
    serializer_class = GateCreateSerializer


class ListSecurityAssignmentView(ListAPIView):

    permission_classes = [IsManagerUser,]
    queryset = SecurityAssignment.objects.select_related('security_agent', 'place').all()
    serializer_class = SecurityAssignmentSerializer

    pagination_class = PageNumberPagination

    filter_backends = [SearchFilter, JalaliDateTimeRangeFilter]
    search_fields = ['security_agent__username', 'place__name']

    # specify target date time field for this model to filter
    date_time_field = 'start_time'


class TrafficView(ListCreateAPIView):

    serializer_class = TrafficSerializer
    queryset = Traffic.objects.select_related('gate__place', 'security_agent', 'automobile').all()
    pagination_class = PageNumberPagination
    filter_backends = [DjangoFilterBackend, JalaliDateTimeRangeFilter]
    date_time_field = 'time'
    filterset_class = TrafficFilterSet

    def get_authenticators(self):
        if self.request.method == 'POST':  # just AI model can create traffic records
            return [AIModelAuthentication(), ]
        else:
            return super().get_authenticators()

    def get_permissions(self):
        if self.request.method == 'POST':
            # as AIModelAuthentication doesn't create user it just authenticates token
            return [AllowAny()]
        else:
            return [IsAuthenticated()]

    def create(self, request, *args, **kwargs):

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=HTTP_201_CREATED)

