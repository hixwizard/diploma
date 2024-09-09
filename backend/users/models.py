from django.contrib.auth.models import AbstractUser
from django.db import models

from core.constans import (
    MAX_EMAIL, MAX_NAME, ROLE_CHOICES, MAX_ROLE_LENGTH, ROLE_CHOICES_LIST)


class User(AbstractUser):
    """
    Модель пользователей.
    """
    email = models.EmailField(
        max_length=MAX_EMAIL,
        unique=True,
        verbose_name='электронная почта'
    )
    username = models.CharField(
        blank=False,
        null=False,
        unique=True,
        max_length=MAX_NAME,
        verbose_name='имя(никнейм)'
    )
    first_name = models.CharField(
        max_length=MAX_NAME,
        verbose_name='Имя'
    )
    last_name = models.CharField(
        max_length=MAX_NAME,
        verbose_name='Фамилия'
    )
    is_subscribed = models.BooleanField(
        default=False
    )
    avatar = models.ImageField(
        default=None,
        null=True,
        upload_to='media/users/',
        verbose_name='фото профиля',
        help_text='фото профиля'
    )
    role = models.CharField(
        max_length=MAX_ROLE_LENGTH,
        choices=ROLE_CHOICES_LIST,
        default=ROLE_CHOICES['user'],
        verbose_name='роль'
    )

    @property
    def is_admin(self):
        return self.role == ROLE_CHOICES['admin']

    @property
    def is_authenticated(self):
        return self.role == ROLE_CHOICES['user']

    @property
    def is_anonymous(self):
        return False

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ('username', 'password', 'first_name', 'last_name')

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.email


class Subscription(models.Model):
    """Модель подписчиков."""
    user = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='subscriptions')
    following = models.ForeignKey(
        User, on_delete=models.CASCADE,
        related_name='followers')

    class Meta:
        verbose_name = 'подписчик'
        verbose_name_plural = 'Подписчики'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='unique_followers'
            ),
        )

    def __str__(self):
        return f'{self.user} подписался на {self.following}'
