import re
from typing import Dict, Any

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

from .models import User


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
