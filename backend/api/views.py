import os
import csv
from io import StringIO
from uuid import uuid4
from tempfile import NamedTemporaryFile

from django.http import FileResponse
from django.db.models import Exists, OuterRef, F
from djoser.views import UserViewSet as DjoserViewSet
from djoser.permissions import CurrentUserOrAdminOrReadOnly
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

from api.filters import RecipeFilter, IngredientFilter
from users.models import User, Subscription
from api.pagination import CustomPagination
from api.permissions import AuthorOrReadOnly, AllowAnyPermission
from recipes.models import (Tag, Recipe, Ingredient, ShortLink,
                            ShoppingCart, FavoriteRecipe,
                            IngredientRecipeAmountModel)
from api.serializers import (UserAvatarUpdateSerializer, TagSerializer,
                             RecipeCreateSerializer, IngredientSerializer,
                             RecipeGETSerializer, RecipeSerializer)
from core.constans import (BASE_DOMAIN, RECIPE_LIMIT, SHORT_LINK_LENGTH,
                           CSV_HEADERS, URL_ID)


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
            return (AllowAnyPermission(),)
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
        elif request.method == 'DELETE':
            if hasattr(request.user, 'avatar'):
                avatar = request.user.avatar
                avatar.delete(save=True)
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            url_path='subscriptions')
    def subscriptions(self, request):
        """
        Получение списка подписчиков.
        """
        page = self.paginate_queryset(self.get_queryset())
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.paginator.get_paginated_response(serializer.data)
        subscriptions = Subscription.objects.filter(user=request.user)
        serializer = self.get_serializer(subscriptions, many=True)
        recipes_limit = int(
            request.query_params.get('recipes_limit', RECIPE_LIMIT)
        )
        filtered_recipes = Recipe.objects.all()
        if recipes_limit:
            filtered_recipes = filtered_recipes[:recipes_limit]
        result = {}
        for subscription in serializer.data:
            user = subscription['url'].split('/')[-URL_ID]
            user_recipes = filtered_recipes.filter(author=user)
            result[user] = {
                'id': user,
                'recipes': RecipeSerializer(user_recipes, many=True).data
            }
        return Response(result, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'],
            url_path='subscribe')
    def subscribe(self, request, pk=None):
        """
        Позволяет подписаться или отписаться от пользователя.
        """
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            if (
                Subscription.objects.filter(
                    user=request.user, following=author
                ).exists() or request.user == author
            ):
                return Response({"error": "Уже подписаны."},
                                status=status.HTTP_400_BAD_REQUEST)
            recipes_limit = int(
                request.query_params.get('recipes_limit', RECIPE_LIMIT)
            )
            Subscription.objects.create(
                user=request.user,
                following=author
            )
            response_data = {
                'message': 'Вы успешно подписались.',
                'recipes': RecipeSerializer(
                    Recipe.objects.filter(author=author)[:int(recipes_limit)],
                    many=True
                ).data
            }
            return Response(response_data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not Subscription.objects.filter(
                user=request.user, following=author
            ).exists():
                return Response({"error": "Нет в подписчиках."},
                                status=status.HTTP_400_BAD_REQUEST)
            subscription = Subscription.objects.get(
                user=request.user, following=author
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Вьюсет тегов.
    """
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    lookup_field = 'id'

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return (AllowAny(),)
        return super().get_permissions()


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
        else:
            queryset = queryset.annotate(
                is_favorited=F('id'),
                is_in_shopping_cart=F('id')
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

    def get_serializer_context(self):
        """
        Возвращает контекст для сериализатора.
        """
        return {'request': self.request}

    def perform_create(self, serializer):
        """
        Создает новый экземпляр модели с указанным автором.
        """
        serializer.save(author=self.request.user)

    def update(self, request, *args, **kwargs):
        """
        Обновляет существующий экземпляр модели.
        """
        instance = self.get_object()
        if instance.author != request.user:
            return Response(
                {"detail": "У вас нет прав на редактирование этого рецепта."},
                status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        """
        Удаляет существующий экземпляр модели.
        """
        instance = self.get_object()
        if instance.author != request.user:
            return Response(
                {"detail": "У вас нет прав на удаление этого рецепта."},
                status=status.HTTP_403_FORBIDDEN)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def _get_or_create_short_link(self, recipe):
        """
        Создание или получение ссылки из БД.
        """
        short_link_obj, created = ShortLink.objects.get_or_create(
            recipe=recipe)
        if created:
            short_link = str(uuid4())[:SHORT_LINK_LENGTH]
            short_link_obj.link = f"{BASE_DOMAIN}/s/{short_link}"
            short_link_obj.save()
            return Response({
                "short_link": short_link_obj.link
            }, status.HTTP_200_OK)
        return Response({
            "short_link": short_link_obj.link
        }, status.HTTP_200_OK)

    @action(detail=True,
            methods=['get'],
            url_path='get-link',
            permission_classes=[AllowAny]
            )
    def get_link(self, request, pk=None):
        """
        Получение ссылки.
        """
        recipe_id = int(pk)
        recipe = get_object_or_404(Recipe, pk=recipe_id)
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
        recipes = self.get_queryset()
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(CSV_HEADERS)
        ingredients_dict = {}
        for recipe in recipes:
            ingredient_amounts = IngredientRecipeAmountModel.objects.filter(
                recipe=recipe)
            for amount in ingredient_amounts:
                ingredient = amount.ingredient
                quantity = amount.amount
                if ingredient.name in ingredients_dict:
                    ingredients_dict[ingredient.name]['quantity'] += quantity
                else:
                    ingredients_dict[ingredient.name] = {
                        'quantity': quantity,
                        'unit': ingredient.measurement_unit
                    }
        for ingredient, data in ingredients_dict.items():
            csv_writer.writerow([ingredient, data['quantity'], data['unit']])
        csv_content = csv_buffer.getvalue()
        temp_file = NamedTemporaryFile(delete=False, suffix='.csv')
        temp_file.write(csv_content.encode('utf-8'))
        temp_file.close()
        response = FileResponse(open(temp_file.name, 'rb'),
                                content_type='text/csv',
                                filename=f"list_{request.user.username}.csv")
        os.unlink(temp_file.name)
        return response

    def _add_or_delete_to_model(self, request, model, pk=None):
        """
        Добавить или удалить элемент в модель.
        """
        recipe = get_object_or_404(Recipe, pk=pk)
        if request.method == 'POST':
            if model.objects.filter(user=request.user, recipe=recipe).first():
                return Response({'error': 'Рецепт уже добавлен в список.'},
                                status=status.HTTP_400_BAD_REQUEST)
            new_instance = model.objects.create(
                user=request.user,
                recipe=recipe)
            serializer = RecipeSerializer(recipe)
            data = serializer.data
            data['model_id'] = new_instance.id
            return Response(data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            if not model.objects.filter(user=request.user,
                                        recipe=recipe).exists():
                return Response(
                    {'error': 'Рецепт не найден в списке.'},
                    status=status.HTTP_400_BAD_REQUEST)
            model.objects.filter(
                user=request.user, recipe=recipe).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='shopping_cart',
            permission_classes=[IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """
        Добавить или удалить из Списка покупок.
        """
        model = ShoppingCart
        return self._add_or_delete_to_model(request, model, pk)

    @action(detail=True,
            methods=['post', 'delete'],
            url_path='favorite',
            permission_classes=[IsAuthenticated])
    def favourites(self, request, pk=None):
        """
        Добавить или удалить в Избранное.
        """
        model = FavoriteRecipe
        return self._add_or_delete_to_model(request, model, pk)
