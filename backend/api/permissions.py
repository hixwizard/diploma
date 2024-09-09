from rest_framework.permissions import BasePermission, SAFE_METHODS


class AllowAnyPermission(BasePermission):
    """
    Доступ для регистрации и просмотра пользователей..
    """
    def has_permission(self, request, view):
        """
        Разрешены только GET и POST запросы.
        """
        allowed_methods = ['GET', 'POST']
        if request.method in allowed_methods:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        """
        Позволяет просматривать:
        список пользователей, провили.
        Зарегистрироваться.
        """
        return True


class AuthorOrReadOnly(BasePermission):
    """
    Доступ Авторизованным пользователям или SAFE_METHODS
    """
    def has_permission(self, request, view):
        """
        Разрешены авторизованные пользователи и безопасные методы.
        """
        return (request.user.is_authenticated
                or request.method in SAFE_METHODS)

    def has_object_permission(self, request, view, obj):
        """
        Доступ автору для изменения или удаления.
        """
        if request.method in SAFE_METHODS:
            return True
        return request.user.is_authenticated or obj.author == request.user
