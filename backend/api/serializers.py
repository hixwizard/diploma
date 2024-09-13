from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.fields import RegexField
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model

from core.constans import ZERO, ONE
from api.mixins import ValidateBase64Mixin, ExtraKwargsMixin
from users.models import Subscription
from recipes.models import (Tag, Recipe, Ingredient, ShortLink,
                            IngredientRecipeAmountModel,
                            FavoriteRecipe, ShoppingCart)

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


class SubscriptionCreateSerializer(serializers.ModelSerializer):
    """
    Сериализатор создания подписок.
    """
    class Meta:
        model = Subscription
        fields = ['id', 'following']
        extra_kwargs = {'following': {'write_only': True}}

    def validate(self, attrs):
        if self.context['request'].user == attrs.get('following'):
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя')
        return attrs


class ListGETSubscriptionsSerialaizer(UserSerializer):
    """
    Сериализатор для получения списка подписчиков с рецептами.
    """
    recipes = serializers.SerializerMethodField('get_recipes', read_only=True)
    recipes_count = serializers.IntegerField(
        source='recipes.count', read_only=True)

    def get_recipes(self, data):
        request = self.context.get('request')
        recipes = data.recipes.all()
        recipes_limit = request.GET.get('recipes_limit')
        if recipes_limit:
            recipes = recipes[:int(recipes_limit)]
        serializer = RecipeSerializer(recipes, many=True)
        return serializer.data


class ListSubscriptionsSerialaizer(serializers.ModelSerializer):
    """
    Сериализатор для создания и удаления подписок.
    """
    class Meta:
        model = Subscription
        fields = ['id', 'following']
        extra_kwargs = {'following': {'write_only': True}}

    def validate(self, validated_data):
        if self.context['request'].user == validated_data.get('following'):
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя')
        return validated_data

    def to_representation(self, instance):
        return ListGETSubscriptionsSerialaizer(
            instance.following,
            context={'request': self.context.get('request')}
        ).data


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

    id = serializers.SerializerMethodField()
    name = serializers.CharField(source='ingredient.name')
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientRecipeAmountModel
        fields = ('id', 'name', 'measurement_unit', 'amount')

    def get_id(self, obj):
        return obj.ingredient.id


class RecipeGETSerializer(serializers.ModelSerializer):
    """
    Этот сериализатор используется для получения полной информации о рецепте,
    включая теги, ингредиенты, автора и статусы избранного и корзины покупок.
    """
    tags = TagSerializer(many=True, read_only=True)
    ingredients = RecipeIngredientSerializer(
        source='ingredient_amounts', many=True, read_only=True)
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
        if value < ONE:
            raise serializers.ValidationError(
                f"Количество ингредиента должно быть больше {ONE}.")
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
        if value == ZERO:
            raise serializers.ValidationError(
                f'Время приготовления должно быть больше {ZERO}'
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
        if self.context['request'].user != instance.author:
            raise serializers.ValidationError(
                'Вы не можете создать рецепт для другого пользователя.')
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


class ShoppingCartSerializer(serializers.ModelSerializer):
    """
    Сериализатор для Списка покупок.
    """
    class Meta:
        model = ShoppingCart
        fields = ('id', 'user', 'recipe')

    def validate(self, data):
        shopping_cart_recipes = ShoppingCart.objects.filter(
            user=self.context['request'].user).values_list('recipe', flat=True)
        if not shopping_cart_recipes.exists():
            raise serializers.ValidationError("Список покупок пуст.")
        return data


class BaseFieldsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для полей при работе с моделями.
    """
    class Meta:
        fields = ['id']


class CreateToModelSerializer(BaseFieldsSerializer):
    """
    Сериализатор для создания в моделях.
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    def create(self, validated_data):
        model_class = self.context.get('model')
        model = globals()[model_class]
        instance = model.objects.create(**validated_data)
        return instance

    def validate(self, data):
        model_class = self.context.get('model')
        model = globals()[model_class]
        if model.objects.filter(
            user=self.context['request'].user, recipe=data['recipe']
        ).exists():
            raise serializers.ValidationError('Рецепт уже добавлен в список.')
        return data


class DeleteFromModelSerializer(BaseFieldsSerializer):
    """
    Сериализатор для удаления из моделей.
    """
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    recipe = serializers.PrimaryKeyRelatedField(queryset=Recipe.objects.all())

    def validate(self, data):
        model_class = self.context.get('model')
        model = globals()[model_class]
        instance = model.objects.filter(
            user=self.context['request'].user,
            recipe=data['recipe']).first()
        if not instance:
            raise serializers.ValidationError('Рецепт не найден в списке')
        return {'instance': instance}


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
