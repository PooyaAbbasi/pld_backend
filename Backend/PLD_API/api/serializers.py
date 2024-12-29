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
    is_manager = serializers.BooleanField(read_only=True)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)
        data['is_manager'] = self.user.is_manager
        return data


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


class JalaliDateTimeField(serializers.DateTimeField):

    def to_representation(self, value):
        aware_local_datetime = timezone.make_aware(value) if timezone.is_naive(value) else value

        local_datetime = aware_local_datetime.astimezone(timezone.get_current_timezone())
        jalali_local_datetime = jdatetime.datetime.fromgregorian(datetime=local_datetime)
        return jalali_local_datetime.strftime(settings.DATETIME_FORMAT)

    def to_internal_value(self, data):
        if not data:
            return None
        try:
            jalali_datetime = jdatetime.datetime.strptime(data, settings.DATETIME_FORMAT)
        except ValueError:
            raise ValidationError("'فرمت زمان ورودی باید به صورت YYYY/MM/DD-HH:MM:SS باشد.'")

        jalali_aware_datetime = timezone.make_aware(jalali_datetime)
        gregorian_tehran_datetime = jalali_aware_datetime.togregorian()
        utc_datetime = timezone.localtime(gregorian_tehran_datetime, timezone=timezone.timezone.utc)
        return utc_datetime


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
