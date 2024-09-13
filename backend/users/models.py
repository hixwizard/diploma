from django.contrib.auth.models import AbstractUser
from django.db import models

from core.constans import MAX_EMAIL, MAX_NAME


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
        blank=True,
        null=True,
        upload_to='media/users/',
        verbose_name='фото профиля',
        help_text='фото профиля'
    )

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
            models.CheckConstraint(
                check=~models.Q(user=models.F('following')),
                name='self_subscription'
            ),
        )

    def __str__(self):
        return f'{self.user} подписался на {self.following}'
