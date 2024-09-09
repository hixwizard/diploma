from rest_framework import serializers

from core.constans import MAX_NAME, MAX_EMAIL


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
            'password': {'allow_blank': True},
        }


class ValidateBase64Mixin:
    """
    Миксин валидации изоражений.
    """
    def validate_image(self, value):
        """
        Проверяет, что поле не равно None.
        """
        if value is None:
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
