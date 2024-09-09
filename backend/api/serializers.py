from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.fields import RegexField
from rest_framework.validators import UniqueTogetherValidator
from django.contrib.auth.hashers import make_password

from api.mixins import ValidateBase64Mixin, ExtraKwargsMixin
from users.models import User, Subscription
from recipes.models import (Tag, Recipe, Ingredient,
                            IngredientRecipeAmountModel,
                            FavoriteRecipe, ShoppingCart)


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
        user = self.context['request'].user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False

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
        read_only_fields = []


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор тегов.
    """
    slug = RegexField(regex=r'^[-a-zA-Z0-9_]+$', required=True)

    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор ингредиентов.
    """
    amount = serializers.IntegerField(read_only=True)

    class Meta:
        model = Ingredient
        fields = ['id', 'name', 'measurement_unit', 'amount']


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для ответа при добавлении рецепта.
    в список покупок или избранное.
    """

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Сериализатор для подписок.
    """
    following = serializers.SlugRelatedField(
        queryset=User.objects.all(), slug_field='email'
    )
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.SerializerMethodField()

    is_subscribed = serializers.BooleanField(default=False)

    class Meta:
        fields = ('id', 'user', 'is_subscribed',
                  'recipes', 'recipes_count', 'following')
        read_only_fields = ('following',)
        model = Subscription
        validators = [
            UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'following')
            )
        ]

    def validate_following(self, attrs):
        """
        Валидация для подписки на самого себя.
        """
        if self.context['request'].user == attrs['following']:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя")
        return super().validate(attrs)

    def get_recipes(self, object):
        """
        Получает список рецептов автора объекта.
        """
        request = self.context.get('request')
        if request is None:
            return []
        limit = request.GET.get('recipes_limit')
        recipes = Recipe.objects.filter(author=object.user)
        if limit:
            recipes = recipes[:int(limit)]
        serializer = RecipeSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, obj):
        """
        Получает количество рецептов автора объекта.
        """
        return obj.user.recipes.count()

    def get_is_subscribed(self, obj):
        """
        Проверяет, подписан ли пользователь на автора объекта.
        """
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, following=obj).exists()


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
    Сериализатор для получения ингредиентов в рецепте.
    """

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit.name'
    )
    amount = serializers.ReadOnlyField()

    class Meta:
        model = IngredientRecipeAmountModel
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeGETSerializer(serializers.ModelSerializer):
    """
    Этот сериализатор используется для получения полной информации о рецепте,
    включая теги, ингредиенты, автора и статусы избранного и корзины покупок.
    """
    tags = TagSerializer(many=True, read_only=True)
    ingredients = IngredientSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    is_favorited = serializers.BooleanField(default=False)
    is_in_shopping_cart = serializers.BooleanField(default=False)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time'
        )
        read_only_fields = ('author', 'tags', 'ingredients')

    def get_is_in_shopping_cart(self, obj):
        """
        Находится ли рецепт в корзине покупок текущего пользователя.
        """
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return ShoppingCart.objects.filter(user=user, recipe=obj).exists()

    def get_is_favorited(self, obj):
        """
        Находится ли рецепт в списке избранного текущего пользователя.
        """
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return FavoriteRecipe.objects.filter(user=user, recipe=obj).exists()

    def to_representation(self, instance):
        """
        Метод для добавления дополнительной информации.
        """
        representation = super().to_representation(instance)
        representation['is_favorited'] = (
            FavoriteRecipe.objects.filter(recipe=instance).exists())
        representation['is_in_shopping_cart'] = (
            ShoppingCart.objects.filter(recipe=instance).exists())
        ingredient_data = []
        for ingredient in representation['ingredients']:
            ingredient_data.append({
                'id': ingredient['id'],
                'name': ingredient['name'],
                'measurement_unit': ingredient['measurement_unit'],
                'amount': 1
            })
        representation['ingredients'] = ingredient_data
        return representation


class IngredientCreateSerializer(serializers.ModelSerializer):
    """
    Серилизатор для Проверки ингредиента при создании рецепта.
    """
    id = serializers.IntegerField()
    amount = serializers.IntegerField(write_only=True)

    class Meta:
        model = IngredientRecipeAmountModel
        fields = ('id', 'amount')

    def validate_amount(self, value):
        """
        Валидация количества.
        """
        if value <= 1:
            raise serializers.ValidationError(
                'Количество должно быть больше нуля.')
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
    name = serializers.CharField(max_length=256)
    text = serializers.CharField()
    cooking_time = serializers.IntegerField()

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'ingredients', 'image',
                  'name', 'text', 'cooking_time')

    def validate_cooking_time(self, value):
        """
        Проверяет, что время приготовления больше нуля.
        """
        if value == 0:
            raise serializers.ValidationError(
                'Время приготовления должно быть больше 0'
            )
        return value

    def create(self, validated_data):
        """
        Создает новый экземпляр модели Recipe.
        """
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        """
        Обновляет экземпляр модели Recipe.
        """
        tags = validated_data.pop('tags', None)
        ingredients = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
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
            ingredient = Ingredient.objects.get(id=ingredient_data['id'])
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
        author_id = self.context.get('request').user.id
        if data.get('author') and data['author'] != author_id:
            raise serializers.ValidationError(
                'Вы можете изменять только свои рецепты.')
        ingredients = data.get('ingredients', [])
        if not ingredients:
            raise serializers.ValidationError('Поле ingredients обязательно.')
        unique_ingredient_ids = set(
            ingredient['id'] for ingredient in ingredients)
        if len(unique_ingredient_ids) != len(ingredients):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными.')
        non_existing_ingredients = [
            ingredient_id for ingredient_id in unique_ingredient_ids
            if not Ingredient.objects.filter(id=ingredient_id).exists()
        ]
        if non_existing_ingredients:
            raise serializers.ValidationError(
                f"Ингредиенты с id {non_existing_ingredients} не существуют.")
        tags = data.get('tags', [])
        if not tags:
            raise serializers.ValidationError('Поле tags обязательно.')
        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги должны быть уникальными.')
        for ingredient_data in data.get('ingredients', []):
            amount = ingredient_data.get('amount')
            if amount <= 0:
                raise serializers.ValidationError(
                    (f'Количество "{ingredient_data["name"]}"'
                     ' должно быть больше нуля.')
                )
        return data

    def to_representation(self, instance):
        """
        Метод для добавления дополнительной информации
        из сериализатора RecipeGETSerializer.
        """
        return RecipeGETSerializer(instance, context=self.context).data
