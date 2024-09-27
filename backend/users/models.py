from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

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
        unique_together = ('user', 'following')

    def clean(self):
        if self.user == self.following:
            raise ValidationError("Нельзя подписаться на себя.")
        if Subscription.objects.filter(
            user=self.user,
            following=self.following
        ).exists():
            raise ValidationError("Подписка уже существует.")

    def __str__(self):
        return f'{self.user} подписался на {self.following}'
