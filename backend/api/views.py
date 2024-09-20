import os
from uuid import uuid4
from io import BytesIO

from django.shortcuts import get_object_or_404
from django.db.models import Prefetch
from django.http import FileResponse
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.db.models import OuterRef, Sum, Exists
from djoser.views import UserViewSet as DjoserViewSet
from djoser.permissions import CurrentUserOrAdminOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from api.filters import RecipeFilter, IngredientFilter
from api.pagination import CustomPagination
from api.permissions import AuthorOrReadOnly
from recipes.models import (Tag, Recipe, Ingredient, ShortLink,
                            ShoppingCart, FavoriteRecipe,
                            IngredientRecipeAmountModel)
from api.serializers import (UserAvatarUpdateSerializer, TagSerializer,
                             RecipeCreateSerializer, IngredientSerializer,
                             RecipeGETSerializer,
                             ShortLinkSerializer, ShoppingCartSerializer,
                             SubscriptionSerializer, FavoriteRecipeSerializer,
                             ListSubscriptionsSerialaizer,)
from core.constans import SHORT_LINK_LENGTH

User = get_user_model()


class UserViewSet(DjoserViewSet):
    """
    Вьюсет пользователей Djoser.
    """
    queryset = User.objects.all()
    pagination_class = CustomPagination
    permission_classes = (CurrentUserOrAdminOrReadOnly,)
    http_method_names = ('get', 'post', 'put', 'delete')
    lookup_field = 'pk'

    def get_permissions(self):
        """
        Права доступа:
        Возможность регистрации,
        просмотра пользователей для гостя.
        """
        if self.action in ('list', 'retrieve', 'create'):
            return (AllowAny(),)
        if self.action == 'me':
            return (IsAuthenticated(),)
        return super().get_permissions()

    @action(methods=('put', 'delete'), detail=False,
            url_path='me/avatar')
    def me_avatar(self, request):
        """
        Обновить или удалить фото профиля.
        """
        if request.method == 'PUT':
            serializer = UserAvatarUpdateSerializer(
                instance=request.user,
                context={'request': request},
                data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        if hasattr(request.user, 'avatar'):
            avatar = request.user.avatar
            avatar.storage == default_storage
            path = avatar.path
            os.path.exists(path)
            default_storage.delete(path)
            setattr(request.user, 'avatar', None)
            request.user.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'], url_path='subscriptions',
            permission_classes=(CurrentUserOrAdminOrReadOnly,))
    def subscriptions(self, request):
        """
        Получение списка подписчиков.
        """
        queryset = User.objects.filter(
            followers__following=request.user
        ).prefetch_related(Prefetch('recipes'))
        page = self.paginate_queryset(queryset)
        serializer = ListSubscriptionsSerialaizer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=(IsAuthenticated,),
        pagination_class=CustomPagination
    )
    def subscribe(self, request, pk=None):
        """
        Позволяет подписаться или отписаться от пользователя.
        """
        following = self.get_object()
        user = request.user
        data = {'following': following.id, 'user': user.id}
        if request.method == 'POST':
            serializer = SubscriptionSerializer(
                data=data,
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            instance = user.subscriptions.filter(following=following).first()
            if instance:
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {'detail': 'Подписка не найдена.'},
                status=status.HTTP_400_BAD_REQUEST)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет тегов.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (AllowAny,)
    pagination_class = None
    lookup_field = 'id'


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет ингредиентов.
    """
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """
    Вьюсет для создания и получения рецептов.
    """
    permission_classes = (AuthorOrReadOnly,)
    pagination_class = CustomPagination
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter
    http_method_names = ('get', 'post', 'patch', 'delete',)

    def get_queryset(self):
        """
        Получение рецептов в зависимости от избранного или списка покупок.
        """
        queryset = Recipe.objects.all()
        if self.request.user.is_authenticated:
            favorite_subquery = FavoriteRecipe.objects.filter(
                user=self.request.user,
                recipe=OuterRef('pk')
            ).values('recipe')
            shopping_cart_subquery = ShoppingCart.objects.filter(
                user=self.request.user,
                recipe=OuterRef('pk')
            ).values('recipe')
            queryset = queryset.annotate(
                is_favorited=Exists(favorite_subquery),
                is_in_shopping_cart=Exists(shopping_cart_subquery)
            )
            if self.request.query_params.get('is_in_shopping_cart'):
                queryset = queryset.filter(is_in_shopping_cart=True)
            if self.request.query_params.get('is_favorited'):
                queryset = queryset.filter(is_favorited=True)
        return queryset

    def get_serializer_class(self):
        """
        Разграничение отображения полей моделей.
        """
        if self.action in ('list', 'retrieve'):
            return RecipeGETSerializer
        return RecipeCreateSerializer

    def _get_or_create_short_link(self, recipe):
        """
        Создание или получение ссылки из БД.
        """
        short_link_obj, created = ShortLink.objects.get_or_create(
            recipe=recipe)
        if created:
            short_link_obj.link = str(uuid4())[:SHORT_LINK_LENGTH]
            short_link_obj.save()
        serializer = ShortLinkSerializer(short_link_obj)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            permission_classes=[AllowAny]
            )
    def get_link(self, request, pk=None):
        """
        Получение ссылки.
        """
        recipe = self.get_object()
        return self._get_or_create_short_link(recipe)

    @action(detail=False,
            methods=['get'],
            url_path='download_shopping_cart',
            permission_classes=[IsAuthenticated]
            )
    def shopping_list(self, request):
        """
        Скачать файл со списком покупок.
        """
        ingredients = IngredientRecipeAmountModel.objects.filter(
            recipe__in=Recipe.objects.filter(
                shoppingcart__user=self.request.user
            )
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_quantity=Sum('amount')
        )

        file_content = "Список покупок:\n"
        if ingredients.exists():
            for item in ingredients:
                file_content += (f"{item['ingredient__name']} - "
                                 f"{item['total_quantity']} "
                                 f"{item['ingredient__measurement_unit']}\n")
        else:
            file_content += "Ваш список покупок пуст.\n"

        file_buffer = BytesIO(file_content.encode('utf-8'))
        return FileResponse(file_buffer,
                            as_attachment=True,
                            filename='shopping_cart.txt',
                            status=status.HTTP_200_OK)

    def _add_or_delete_to_model(
            self, request, serializer_class, model, pk=None
    ):
        """
        Добавить или удалить элемент в модель.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        user = request.user
        data = {'user': user.id, 'recipe': recipe.id}
        serializer = serializer_class(data=data, context={'request': request})
        if request.method == 'POST':
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(status=status.HTTP_201_CREATED)
        if request.method == 'DELETE':
            serializer.is_valid(raise_exception=True)
            instance = model.objects.filter(user=user, recipe=recipe).first()
            if instance:
                instance.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            return Response(
                {"detail": "Рецепт уже удалён."},
                status=status.HTTP_404_NOT_FOUND)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='favorite',
            permission_classes=[CurrentUserOrAdminOrReadOnly])
    def add_to_favorites(self, request, pk=None):
        """
        Добавляет или удаляет рецепты из избранного.
        """
        return self._add_or_delete_to_model(
            request, FavoriteRecipeSerializer, FavoriteRecipe, pk)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='shopping_cart',
            permission_classes=[CurrentUserOrAdminOrReadOnly])
    def add_to_shopping_cart(self, request, pk=None):
        """
        Добавляет или удаляет рецепты из списка покупок.
        """
        return self._add_or_delete_to_model(
            request, ShoppingCartSerializer, ShoppingCart, pk)
