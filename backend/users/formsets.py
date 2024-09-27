from django.contrib import admin
from django.core.exceptions import ValidationError

from .models import Subscription
from core.constans import FIELD_TO_EDIT


class SubscriptionInline(admin.TabularInline):
    """
    Валидация подписчиков.
    """
    model = Subscription
    extra = FIELD_TO_EDIT

    def save_related(self, request, form, change):
        self.validate_subscriptions(form.instance.subscriptions.all())
        super().save_related(request, form, change)

    def validate_subscriptions(self, subscriptions):
        for obj in subscriptions:
            if obj.user.id == obj.following.id:
                raise ValidationError('Нельзя подписаться на себя.')
            if obj.following.subscriptions.filter(user=obj.user).exists():
                raise ValidationError('Подписка уже есть.')
