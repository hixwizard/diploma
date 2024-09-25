from django import forms
from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from users.models import User, Subscription


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = (
            'email', 'username', 'first_name',
            'last_name', 'password',
            'is_subscribed', 'avatar'
        )

    def clean_password(self):
        return self.initial['password']


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    form = UserChangeForm
    list_display = (
        'id', 'email', 'password', 'username',
        'first_name', 'last_name', 'avatar_image'
    )
    list_filter = ('email', 'username',)
    search_fields = ('email', 'username', 'first_name', 'last_name',)

    @admin.display(ordering='avatar')
    def avatar_image(self, obj):
        if obj.avatar:
            return f'<img src="{obj.avatar.url}" width="50px" height="50px">'
        return '-'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_username', 'following_username')
    list_filter = ('user',)
    search_fields = ('user__username', 'following__username')

    @admin.display(ordering='user__username')
    def user_username(self, obj):
        return obj.user.username

    @admin.display(ordering='following__username')
    def following_username(self, obj):
        return obj.following.username


admin.site.unregister(Group)
