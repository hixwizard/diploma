from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.fields import RegexField
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Prefetch
from django.db.models.signals import pre_delete
from django.dispatch import receiver
from django.core.files.storage import default_storage

from core.constans import MIN_COOKING_TIME, MIN_AMOUNT
from api.mixins import ValidateBase64Mixin, ExtraKwargsMixin
from users.models import Subscription
from recipes.models import (Tag, Recipe, Ingredient, ShortLink,
                            IngredientRecipeAmountModel,
                            FavoriteRecipe, ShoppingCart,
                            BaseUserRecipe, TagRecipe)
User = get_user_model()


class UserSerializer(serializers.ModelSerializer, ValidateBase64Mixin):
    """
    Сериализатор пользователей.
    """
    is_subscribed = serializers.BooleanField(default=False)
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 'first_name',
            'last_name', 'is_subscribed', 'avatar')

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли текущий пользователь на данного автора.
        """
        return obj.followers.filter(
            user=self.context['request'].user, author=obj).exists()

    def get_avatar(self, obj):
        """
        Возвращает URL аватара пользователя или None, если аватара нет.
        """
        if obj.avatar:
            return obj.avatar.url
        return None


class UserCreateSerializer(serializers.ModelSerializer, ExtraKwargsMixin):
    """
    Сериализатор регистрации пользователей.
    """

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation.pop('password', None)
        return representation

    class Meta:
        model = User
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'password')


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор тегов.
    """
    slug = RegexField(regex=r'^[-a-zA-Z0-9_]+$', required=True)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


@receiver(pre_delete, sender=Recipe)
@transaction.atomic
def delete_recipe_image(sender, instance, **kwargs):
    """
    Удаление изображения рецепта из БД.
    """
    if hasattr(instance, 'image') and instance.image:
        file_path = instance.image.path
        default_storage.delete(file_path)
        instance.image.delete(save=False)
    return True


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор ингредиентов.
    """
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответа при получении рецепта.
    """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        read_only_fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор создания подписок.
    """

    class Meta:
        model = Subscription
        fields = ('id', 'user', 'following')

    def validate_following(self, value):
        if value.followers.filter(
                user=self.context['request'].user
        ).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя.')
        return value

    def to_representation(self, instance):
        return ListSubscriptionsSerialaizer(
            instance, context=self.context).data


class ListSubscriptionsSerialaizer(UserSerializer):
    """
    Сериализатор для получения списка подписчиков с рецептами.
    """
    recipes = serializers.SerializerMethodField('get_recipes', read_only=True)
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    class Meta:
        model = User
        fields = UserSerializer.Meta.fields + (
            'recipes',
            'recipes_count',
        )
        read_only_fields = (
            'email', 'username', 'first_name',
            'last_name'
        )

    def get_recipes_count(self, obj):
        return obj.following.recipes.count()

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes = obj.following.recipes.all()
        limit = request.GET.get('limit') or None
        if limit and not limit.isdigit():
            raise serializers.ValidationError('Лимит должен быть целым числом')
        recipes = recipes[:limit] if limit else recipes
        serializer = RecipeSerializer(recipes, many=True)
        return serializer.data


class UserAvatarUpdateSerializer(
    serializers.ModelSerializer,
    ValidateBase64Mixin
):
    """
    Сериализатор для обновления аватара пользователя.
    """
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = ('avatar',)


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для промежуточной модели рецепты/ингредиенты.
    """

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipeAmountModel
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeGETSerializer(serializers.ModelSerializer):
    """
    Этот сериализатор используется для получения полной информации о рецепте,
    включая теги, ингредиенты, автора и статусы избранного и корзины покупок.
    """
    tags = serializers.SerializerMethodField()

    ingredients = serializers.SerializerMethodField()

    author = UserSerializer(read_only=True)
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'name', 'text', 'cooking_time',
            'author', 'is_favorited', 'is_in_shopping_cart',
            'image', 'ingredients'
        )
        read_only_fields = ('author',)

    def get_tags(self, recipe):
        queryset = TagRecipe.objects.filter(recipe=recipe)
        tags = Tag.objects.all().prefetch_related(
            Prefetch('tagrecipe_set', queryset=queryset))
        return TagSerializer(tags, many=True).data

    def get_ingredients(self, recipe):
        queryset = IngredientRecipeAmountModel.objects.filter(recipe=recipe)
        return RecipeIngredientSerializer(queryset, many=True).data


class IngredientCreateSerializer(serializers.ModelSerializer):
    """
    Серилизатор для Проверки ингредиента при создании рецепта.
    """
    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(), required=True)
    amount = serializers.IntegerField(write_only=True)

    class Meta:
        model = IngredientRecipeAmountModel
        fields = ('id', 'amount')

    def validate_amount(self, value):
        if value < MIN_AMOUNT:
            raise serializers.ValidationError(
                f'Количество ингредиента должно быть больше {MIN_AMOUNT}.')
        return value


class RecipeCreateSerializer(serializers.ModelSerializer, ValidateBase64Mixin):
    """
    Сериализатор для создания и обновления рецептов.
    """
    tags = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Tag.objects.all(), required=True)
    ingredients = IngredientCreateSerializer(
        many=True, write_only=True, required=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients', 'image',
                  'name', 'text', 'cooking_time')

    def validate_cooking_time(self, value):
        """
        Проверяет, что время приготовления больше нуля.
        """
        if value <= MIN_COOKING_TIME:
            raise serializers.ValidationError(
                f'Время приготовления должно быть больше {MIN_COOKING_TIME}'
            )
        return value

    def create(self, validated_data):
        """
        Создает новый экземпляр модели Recipe.
        """
        author = self.context['request'].user
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(author=author, **validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """
        Обновляет экземпляр модели Recipe.
        """
        tags = validated_data.pop('tags', [])
        ingredients = validated_data.pop('ingredients', [])
        instance = super().update(instance, validated_data)
        instance.tags.set(tags)
        instance.ingredients.clear()
        self.create_ingredients(instance, ingredients)
        instance.save()
        return instance

    def create_ingredients(self, recipe, ingredients_data):
        """
        Наполняет рецепт ингредиентами.
        """
        ingredients_list = []
        for ingredient_data in ingredients_data:
            ingredient = ingredient_data['id']
            amount = ingredient_data['amount']
            ingredients_list.append(IngredientRecipeAmountModel(
                recipe=recipe,
                amount=amount,
                ingredient=ingredient
            ))
        IngredientRecipeAmountModel.objects.bulk_create(ingredients_list)

    def validate(self, data):
        """
        Проверяет, что ингредиенты и теги уникальны и существуют.
        и что они не пустые.
        """
        ingredients = data.get('ingredients', [])
        if not ingredients:
            raise serializers.ValidationError('Поле ingredients обязательно.')
        unique_ingredient_ids = set(
            ingredient['id'] for ingredient in ingredients)
        if len(unique_ingredient_ids) != len(ingredients):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными.')
        tags = data.get('tags', [])
        if not tags:
            raise serializers.ValidationError('Поле tags обязательно.')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги должны быть уникальными.')
        return data

    def to_representation(self, instance):
        """
        Метод для добавления дополнительной информации
        из сериализатора RecipeGETSerializer.
        """
        return RecipeGETSerializer(instance, context=self.context).data


class BaseUserRecipeSerializer(serializers.ModelSerializer):
    """
    Абстрактный базовый сериализатор для объектов пользователь/рецепт.
    """

    class Meta:
        abstract = True
        fields = ('user', 'recipe')
        validators = [
            UniqueTogetherValidator(
                queryset=BaseUserRecipe.objects.all(),
                fields=['user', 'recipe']
            )
        ]

    def validate(self, attrs=None):
        """
        Проверка валидности данных перед сохранением или удалением.
        """
        if not attrs:
            return {}
        user = attrs.get('user', self.context.get('request').user)
        recipe = attrs.get('recipe')
        if self.context['request'].method == 'POST':
            if self.Meta.model.objects.filter(
                user=user, recipe=recipe
            ).exists():
                raise ValidationError('Рецепт уже добавлен.')
        if self.context['request'].method == 'DELETE':
            if not self.Meta.model.objects.filter(
                user=user, recipe=recipe
            ).exists():
                raise ValidationError('Рецепт уже удалён.')
        return attrs

    def create(self, validated_data):
        """
        Создание нового экземпляра модели.
        """
        return self.Meta.model.objects.create(**validated_data)

    def delete(self, instance):
        """
        Удаление экземпляра модели.
        """
        return instance.delete()

    def to_representation(self, instance):
        """
        Формирование представления для ответа API.
        """
        return RecipeSerializer(instance, context=self.context).data


class ShoppingCartSerializer(BaseUserRecipeSerializer):
    """
    Сериализатор для корзины пользователя.
    """
    class Meta(BaseUserRecipeSerializer.Meta):
        model = ShoppingCart
        fields = ['id', 'recipe', 'user']


class FavoriteRecipeSerializer(BaseUserRecipeSerializer):
    """
    Сериализатор для избранных рецептов пользователя.
    """
    class Meta(BaseUserRecipeSerializer.Meta):
        model = FavoriteRecipe
        fields = ['id', 'recipe', 'user']


class ShortLinkSerializer(serializers.ModelSerializer):
    """
    Сериализатор для короткой ссылки.
    """
    short_link = serializers.SerializerMethodField()

    class Meta:
        model = ShortLink
        fields = ('link',)

    def to_representation(self, instance):
        short_link = instance.link
        return {"short-link": short_link}
