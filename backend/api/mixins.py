from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator

from users.models import Subscription
from core.constans import MAX_NAME, MAX_EMAIL, EMPTY_VALUES


class ExtraKwargsMixin:
    """
    Миксин валидации пользователей.
    """
    class Meta:
        extra_kwargs = {
            'username': {
                'max_length': MAX_NAME,
                'regex': r'`^[w.@+-]+Z`',
            },
            'email': {'max_length': MAX_EMAIL, 'validators': []},
            'first_name': {'max_length': MAX_NAME},
            'last_name': {'max_length': MAX_NAME},
            'password': {'allow_blank': False},
        }


class ValidateBase64Mixin:
    """
    Миксин валидации изоражений.
    """
    def validate_image(self, value):
        """
        Проверяет, что поле не равно None.
        """
        if value in EMPTY_VALUES:
            raise serializers.ValidationError(
                'Поле image обязательно, не может быть пустым.')
        return value

    def validate_avatar(self, value):
        """
        Проверяет, что поле передано.
        """
        if not value:
            raise serializers.ValidationError('Поле avatar обязательно.')
        return value


class UniqueSubscriptionMixin:
    """
    Миксин для валидации уникальности подписки.
    """

    class Meta:
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'following')
            )
        ]
