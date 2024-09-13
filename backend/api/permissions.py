from rest_framework.permissions import BasePermission, SAFE_METHODS


class AuthorOrReadOnly(BasePermission):
    """
    Доступ Авторизованным пользователям или SAFE_METHODS
    """
    def has_permission(self, request, view):
        """
        Разрешены авторизованные пользователи и безопасные методы.
        """
        return (
            request.user.is_authenticated
            or request.method in SAFE_METHODS
        )

    def has_object_permission(self, request, view, obj):
        """
        Доступ автору для изменения или удаления.
        """
        return (request.method in SAFE_METHODS
                or obj.author == request.user)
