from typing import Dict, Any

from djoser.serializers import (
    UserCreateSerializer as BaseUserCreateSerializer,
    UserSerializer as BaseUserSerializer,
    UserDeleteSerializer as BaseUserDeleteSerializer,
)
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer as BaseTokenObtainPairSerializer


class UserCreateSerializer(BaseUserCreateSerializer):

    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)

    profile_image = serializers.ImageField(required=False, allow_null=True, write_only=True)

    class Meta(BaseUserCreateSerializer.Meta):
        model = BaseUserCreateSerializer.Meta.model
        fields = BaseUserCreateSerializer.Meta.fields + ('first_name', 'last_name', 'profile_image')


class UserSerializer(BaseUserSerializer):

    class Meta(BaseUserSerializer.Meta):
        model = BaseUserSerializer.Meta.model
        fields = BaseUserSerializer.Meta.fields + (
            'username', 'first_name', 'last_name', 'profile_image',
        )

        read_only_fields = ('id',)
        extra_kwargs = {
            'username': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
            'profile_image': {'required': False},
            'is_active': {'required': False},
        }


class TokenObtainPairSerializer(BaseTokenObtainPairSerializer):
    """
        overrides BaseTokenObtainPairSerializer in order to add 'is_manager' filed to response data.
    """
    is_manager = serializers.BooleanField(read_only=True)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, str]:
        data = super().validate(attrs)
        data['is_manager'] = self.user.is_staff or self.user.is_superuser
        return data
