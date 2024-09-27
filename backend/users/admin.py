from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import AdminPasswordChangeForm

from users.models import User, Subscription


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Административная панель пользователя.
    """
    list_display = (
        'id', 'email', 'username', 'first_name', 'last_name', 'avatar_image'
    )
    list_filter = ('email', 'username',)
    search_fields = ('email', 'username', 'first_name', 'last_name',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'avatar')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    change_password_form = AdminPasswordChangeForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2'),
        }),
    )
    ordering = ('email',)

    @admin.display(ordering='avatar')
    def avatar_image(self, obj):
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="50px" height="50px">'
        return '-'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Административная панель подписок.
    """
    list_display = ('id', 'user_username', 'following_username')
    list_filter = ('user',)
    search_fields = ('user__username', 'following__username')
    inlines = [SubscriptionInline]

    @admin.display(ordering='user__username')
    def user_username(self, obj):
        return obj.user.username

    @admin.display(ordering='following__username')
    def following_username(self, obj):
        return obj.following.username


admin.site.unregister(Group)
