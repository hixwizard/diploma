import os
from uuid import uuid4
from io import BytesIO

from django.http import FileResponse
from django.core.files.storage import default_storage
from django.contrib.auth import get_user_model
from django.db.models import OuterRef, Sum, Exists
from djoser.views import UserViewSet as DjoserViewSet
from djoser.permissions import CurrentUserOrAdminOrReadOnly
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from api.filters import RecipeFilter, IngredientFilter
from users.models import Subscription
from api.pagination import CustomPagination
from api.permissions import AuthorOrReadOnly
from recipes.models import (Tag, Recipe, Ingredient, ShortLink,
                            ShoppingCart, FavoriteRecipe,
                            IngredientRecipeAmountModel)
from api.serializers import (UserAvatarUpdateSerializer, TagSerializer,
                             RecipeCreateSerializer, IngredientSerializer,
                             RecipeGETSerializer, RecipeSerializer,
                             ShortLinkSerializer,
                             ShoppingCartSerializer,
                             DeleteFromModelSerializer,
                             CreateToModelSerializer,
                             ListGETSubscriptionsSerialaizer,
                             ListSubscriptionsSerialaizer,
                             SubscriptionCreateSerializer)
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
        elif self.action == 'me':
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
        else:
            if hasattr(request.user, 'avatar'):
                avatar = request.user.avatar
                avatar.storage == default_storage
                path = avatar.path
                os.path.exists(path)
                default_storage.delete(path)
                setattr(request.user, 'avatar', None)
                request.user.save()
                return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            url_path='subscriptions',
            permission_classes=(CurrentUserOrAdminOrReadOnly,))
    def subscriptions(self, request):
        """
        Получение списка подписчиков.
        """
        queryset = User.objects.prefetch_related('recipes').filter(
            followers__user=request.user)
        page = self.paginate_queryset(queryset)
        serializer = ListGETSubscriptionsSerialaizer(
            page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=['post', 'delete'],
        url_path='subscribe',
        permission_classes=(IsAuthenticated,),
        serializer_class=ListSubscriptionsSerialaizer,
        pagination_class=CustomPagination
    )
    def subscribe(self, request, pk=None):
        """
        Позволяет подписаться или отписаться от пользователя.
        """
        following = self.get_object()
        if request.method == 'POST':
            serializer = SubscriptionCreateSerializer(
                data={'following': following.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        subscription = Subscription.objects.filter(
            user=request.user, following=following).first()
        if subscription:
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_400_BAD_REQUEST)


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
        tag_filter = self.request.query_params.getlist('tags')
        if tag_filter:
            queryset = queryset.filter(
                tags__slug__in=[tag.lower() for tag in tag_filter])
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
        if self.request.user.is_authenticated:
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
            permission_classes=[AuthorOrReadOnly]
            )
    def shopping_list(self, request):
        """
        Скачать файл со списком покупок.
        """
        user = self.request.user
        if request.data:
            serializer = ShoppingCartSerializer(data=request.data)
            if serializer.is_valid():
                shopping_cart_recipes = serializer.validated_data['recipe']
            else:
                shopping_cart_recipes = []
        else:
            shopping_cart_recipes = ShoppingCart.objects.filter(
                user=user).values_list('recipe', flat=True)
        ingredients = IngredientRecipeAmountModel.objects.filter(
            recipe__in=shopping_cart_recipes
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_quantity=Sum('amount')
        )
        file_content = "Список покупок:\n"
        for item in ingredients:
            file_content += (f"{item['ingredient__name']} - "
                             f"{item['total_quantity']} "
                             f"{item['ingredient__measurement_unit']}\n")
        file_buffer = BytesIO(file_content.encode('utf-8'))
        return FileResponse(file_buffer,
                            as_attachment=True,
                            filename='shopping_cart.txt')

    def _add_or_delete_to_model(self, request, model_name, pk=None):
        """
        Добавить или удалить элемент в модель.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            serializer = CreateToModelSerializer(
                data={'user': request.user, 'recipe': recipe},
                context={'request': request, 'model': model_name}
            )
            validated_data = serializer.validate(serializer.initial_data)
            new_instance = serializer.create(validated_data)
            serializer = RecipeSerializer(recipe)
            data = serializer.data
            data['model_id'] = new_instance.id
            return Response(data, status=status.HTTP_201_CREATED)
        else:
            serializer = DeleteFromModelSerializer(
                data={'recipe': recipe},
                context={'request': request, 'model': model_name}
            )
            instance_data = serializer.validate({'recipe': recipe})
            ModelClass = globals()[model_name]
            model_instance = ModelClass.objects.get(
                user=request.user,
                recipe=instance_data['instance'].recipe)
            model_instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='shopping_cart',
            permission_classes=[CurrentUserOrAdminOrReadOnly])
    def shopping_cart(self, request, pk=None):
        """
        Добавить или удалить из Списка покупок.
        """
        model_name = ShoppingCart.__name__
        return self._add_or_delete_to_model(request, model_name, pk)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='favorite',
            permission_classes=[CurrentUserOrAdminOrReadOnly])
    def favorites(self, request, pk=None):
        """
        Добавить или удалить в Избранное.
        """
        model_name = FavoriteRecipe.__name__
        return self._add_or_delete_to_model(request, model_name, pk)
