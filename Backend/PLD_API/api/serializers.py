import re
from typing import Dict, Any

from django.utils import timezone
from django.conf import settings
import jdatetime

from djoser.serializers import (
    UserCreateSerializer as BaseUserCreateSerializer,
    UserSerializer as BaseUserSerializer,
    SetPasswordSerializer as BaseSetPasswordSerializer,
)
from rest_framework import serializers
from django.http import HttpRequest

from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer as BaseTokenObtainPairSerializer
)

from .models import *


def phone_number_validator(phone_number: str) -> str:
    """
    Validates phone number to contains 11 digits and only 11 digits, and begins with 09
    :return: validated phone number, or raises ValidationError
    """
    if not re.fullmatch(r'09\d{9}', phone_number):
        raise ValidationError(detail="شماره تلفن باید حتما ۱۱ رقم باشد و با 09 شروع شود.")

    return phone_number


class JalaliDateTimeField(serializers.DateTimeField):
    """
    Custom DateTimeField that converts between UTC Gregorian datetimes and
    Jalali formatted strings (using settings.DATETIME_FORMAT).

    - to_representation: Converts a datetime (naive or UTC) to the current timezone,
      then to Jalali and returns a formatted string.
    - to_internal_value: Parses a Jalali formatted string and converts it to a UTC datetime.
    """
    def to_representation(self, value):
        aware_dt = timezone.make_aware(value) if timezone.is_naive(value) else value
        local_dt = aware_dt.astimezone(timezone.get_current_timezone())
        jalali_dt = jdatetime.datetime.fromgregorian(datetime=local_dt)
        return jalali_dt.strftime(settings.DATETIME_FORMAT)

    def to_internal_value(self, data) -> timezone.datetime | None:
        if not data:
            return None
        try:
            # Parse input string using the expected Jalali format.
            jalali_dt = jdatetime.datetime.strptime(data, settings.DATETIME_FORMAT)
        except ValueError:
            raise ValidationError(f"'فرمت زمان ورودی باید به صورت {settings.DATETIME_FORMAT} باشد.'")

        jalali_aware = timezone.make_aware(jalali_dt)

        gregorian_dt = jalali_aware.togregorian()
        utc_dt = timezone.localtime(gregorian_dt, timezone=timezone.timezone.utc)
        return utc_dt


class UserCreateSerializer(BaseUserCreateSerializer):

    is_manager = serializers.BooleanField(required=False)

    class Meta(BaseUserCreateSerializer.Meta):
        model = BaseUserCreateSerializer.Meta.model
        fields = (BaseUserCreateSerializer.Meta.fields + (
            'first_name', 'last_name', 'profile_image', 'is_manager', 'phone_number',
        ))
        extra_kwargs = {
            'phone_number': {'required': False, 'validators': [phone_number_validator, ]},
        }


class UserSerializer(BaseUserSerializer):

    is_manager = serializers.BooleanField(required=False)

    class Meta(BaseUserSerializer.Meta):
        model = BaseUserSerializer.Meta.model
        fields = BaseUserSerializer.Meta.fields + (
            'username', 'first_name', 'last_name',
            'profile_image', 'is_manager', 'phone_number',

        )

        read_only_fields = ('id',)
        extra_kwargs = {
            'username': {'required': True},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'profile_image': {'required': False},
            'is_manager': {'required': False},
            'phone_number': {'required': False, 'validators': [phone_number_validator, ]},
        }


class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    """
        overrides BaseTokenObtainPairSerializer in order to add 'is_manager' filed to response data.
    """

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)

        is_user_manager = self.user.is_manager
        print(self.context.get('request').COOKIES.get('place_id'))
        if not is_user_manager:  # to assign security agents
            place = self.__get_place_obj_from_cookie()
            # create an assignment or rais ValidationError if any assignment already exists.
            SecurityAssignment.assign_security_agent(self.user, place)

        data['is_manager'] = is_user_manager
        return data

    def __get_place_obj_from_cookie(self) -> Place:
        """
        :return: Place object with `place_id` which is provided in cookies of request.
                else raises ValidationError.
        """
        request: HttpRequest = self.context.get('request')
        place_id = request.COOKIES.get('place_id')
        print(request.COOKIES)
        return self.__class__.__check_and_get_place(place_id)

    @staticmethod
    def __check_and_get_place(place_id) -> Place:
        if place_id is None:
            raise (ValidationError('اطلاعات مربوط به مکان برای ورود کاربر حراست نیاز است،'
                                   ' باید مکان برای این سیستم تنظیم شود.'))

        else:
            try:
                place = Place.objects.get(pk=place_id)
            except Place.DoesNotExist:
                raise ValidationError('مکانی با این اطلاعات در پایگاه داده موجود نیست.')

            # in database is_assigned is False but in cookie exists
            # manager should use remove endpoint and assign this place agin
            if not place.is_assigned:
                raise ValidationError('این مکان تنظیم نشده، مدیریت باید ابتدا آنرا تنظیم کند.')

        return place


class CurrentUserSerializer(UserSerializer):

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields
        read_only_fields = ('id', 'username', 'first_name', 'last_name', 'profile_image', 'is_manager', 'phone_number')


class SetPasswordSerializer(serializers.Serializer):

    new_password = serializers.CharField(write_only=True, required=True)


class AutomobileSerializer(serializers.ModelSerializer):

    is_permitted = serializers.BooleanField(read_only=True)

    class Meta:
        model = Automobile
        fields = ['plate', 'name_and_model', 'color', 'owner_username',
                  'owner_first_name', 'owner_last_name', 'is_permitted', 'is_allways_permitted']
        required_fields = ('plate',)
        extra_kwargs = {
            'owner_username': {'default': None, 'required': False},
            'is_allways_permitted': {'write_only': True, 'required': False, 'default': False},
        }
        unique_together = ('plate', 'owner_username')

    def plate_validator(self, plate: str) -> str:
        pattern = re.compile(self.Meta.model.FULL_MATCH_PLATE_PATTERN)
        clean_plate = plate.strip()
        if not pattern.match(clean_plate):
            raise ValidationError("Invalid plate format")

        return clean_plate


class AutomobileUpdateSerializer(AutomobileSerializer):
    class Meta(AutomobileSerializer.Meta):
        fields = AutomobileSerializer.Meta.fields
        read_only_fields = ['plate',]


class AutomobileDetailSerializer(AutomobileSerializer):

    active_permission = serializers.SerializerMethodField()

    class Meta(AutomobileSerializer.Meta):
        fields = ['plate', 'color', 'name_and_model',
                  'owner_username', 'owner_first_name', 'owner_last_name',
                  'active_permission', 'is_allways_permitted'
                  ]
        read_only_fields = ['plate', 'color', 'name_and_model',
                            'owner_username', 'owner_first_name', 'owner_last_name',
                            'active_permission', 'is_allways_permitted']

        extra_kwargs = {
            'is_allways_permitted': {'write_only': False},
        }

    def get_active_permission(self, obj: Automobile) -> Dict | None:
        active_permission = obj.get_active_permission()
        if active_permission:
            return TemporaryPermissionSerializer(active_permission).data
        return None


class TemporaryPermissionSerializer(serializers.ModelSerializer):

    automobile = serializers.PrimaryKeyRelatedField(queryset=Automobile.objects.all())
    from_time = JalaliDateTimeField()
    to_time = JalaliDateTimeField()
    granted_by = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = TemporaryPermission
        fields = '__all__'

    def validate(self, attrs):
        data = super().validate(attrs)

        from_time = data.get('from_time')
        to_time = data.get('to_time')
        automobile = data.get('automobile')
        pk = None

        # set instance data if they are not exists in patch data.
        if self.context.get('request').method == 'PATCH':
            from_time = from_time if (from_time is not None) else self.instance.from_time
            to_time = to_time if (to_time is not None) else self.instance.to_time
            automobile = automobile if (automobile is not None) else self.instance.automobile
            pk = self.instance.pk

        # check if from_time is before that to_time.
        if from_time >= to_time:
            raise ValidationError('زمان شروع مجوز باید قبل از زمان پایان آن باشد!')

        if to_time <= timezone.now():
            raise ValidationError('زمان پایان مجوز باید برای آینده باشد!')

        new_permission = TemporaryPermission(pk=pk, from_time=from_time, to_time=to_time, automobile=automobile)

        # Check for conflicts with current or other permissions in the future.
        if TemporaryPermission.objects.filter(
                TemporaryPermission.conflict_with_current_or_future_permissions_conditions(new_permission)
        ).exists():
            raise ValidationError('زمان مجوز داده شده با زمان مجوز های کنونی یا مجوز های آینده تداخل دارد!')

        return data


class ModifyTempPermissionSerializer(TemporaryPermissionSerializer):

    class Meta(TemporaryPermissionSerializer.Meta):
        model = TemporaryPermissionSerializer.Meta.model
        fields = TemporaryPermissionSerializer.Meta.fields
        read_only_fields = ['automobile', 'id']


class TempPermissionDetailSerializer(TemporaryPermissionSerializer):

    granted_by = UserSerializer(read_only=True)

    class Meta(TemporaryPermissionSerializer.Meta):
        model = TemporaryPermissionSerializer.Meta.model
        fields = TemporaryPermissionSerializer.Meta.fields


class GateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gate
        fields = ['id', 'name', 'type', 'permission_needed']
        read_only_fields = ['id',]


class PlaceSerializer(serializers.ModelSerializer):

    gates = GateSerializer(many=True, read_only=True)
    is_this_client_place = serializers.SerializerMethodField()

    class Meta:
        model = Place
        fields = ['id', 'name', 'gates', 'is_assigned', 'is_this_client_place']
        read_only_fields = ['id', 'is_this_client_place', 'is_assigned']

    def get_is_this_client_place(self, obj: Place) -> bool:
        client_place_id = self.context['request'].COOKIES.get('place_id')
        if client_place_id is not None:
            return int(client_place_id) == obj.id and obj.is_assigned
        else:
            return False


class GateCreateSerializer(GateSerializer):
    place = serializers.PrimaryKeyRelatedField(queryset=Place.objects.all())

    class Meta(GateSerializer.Meta):
        model = Gate
        fields = GateSerializer.Meta.fields + ['place']


class SecurityAssignmentSerializer(serializers.ModelSerializer):
    start_time = JalaliDateTimeField(read_only=True)
    end_time = JalaliDateTimeField(read_only=True)
    security_agent = serializers.SlugRelatedField(slug_field='username', read_only=True)
    place = serializers.SlugRelatedField(slug_field='name', read_only=True)

    class Meta:
        model = SecurityAssignment
        fields = ['place', 'security_agent', 'start_time', 'end_time',]

