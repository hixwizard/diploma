from django.db import models
from django.contrib.auth import get_user_model

from core.constans import MAX_TAG, MAX_INGREDIENT, MAX_UNIT, RECIPE_MAX_FIELDS

User = get_user_model()


class Tag(models.Model):
    """
    Модель тегов.
    """
    name = models.CharField(
        max_length=MAX_TAG,
        blank=False,
        null=False,
        unique=True,
        verbose_name='Название'
    )
    slug = models.CharField(
        max_length=MAX_TAG,
        blank=False,
        null=False,
        unique=True,
        verbose_name='Идентификатор'
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    """
    Модель ингридиентов.
    """
    name = models.CharField(
        max_length=MAX_INGREDIENT,
        blank=False,
        null=False,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        blank=False,
        null=False,
        max_length=MAX_UNIT,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        constraints = [
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredients')
        ]

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """
    Модель рецептов.
    """
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        db_index=True
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientRecipeAmountModel',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        'Tag',
        through='TagRecipe',
        related_name='recipes'
    )

    image = models.ImageField(
        upload_to='media/recipes/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    name = models.CharField(
        blank=False,
        null=False,
        max_length=RECIPE_MAX_FIELDS,
        verbose_name='Название'
    )
    text = models.CharField(
        blank=False,
        null=False,
        max_length=RECIPE_MAX_FIELDS,
        verbose_name='Описание'
    )
    cooking_time = models.PositiveSmallIntegerField(
        blank=False,
        null=False,
        verbose_name='Время приготовления',
        help_text='В минутах'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class TagRecipe(models.Model):
    """
    Промежуточная модель тегов к рецепту.
    """
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE
    )

    def __str__(self):
        return f'{self.tag} {self.recipe}'


class IngredientRecipeAmountModel(models.Model):
    """
    Промежуточная модель ингредиентов к рецепту c количеством.
    """
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_amounts',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='recipe_amounts',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        'Количество',
        blank=False,
        null=False,
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Кол-во ингредиента в рецепте'
        constraints = [
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredients')
        ]

    def __str__(self):
        return (f'Ингредиент {self.ingredient.name} {self.amount}'
                f' {self.ingredient.measurement_unit}')


class ShortLink(models.Model):
    """
    Модель которких ссылок.
    """
    recipe = models.OneToOneField(
        'Recipe',
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name='Рецепт'
    )
    link = models.URLField(
        unique=True,
        verbose_name='Короткая ссылка'
    )

    class Meta:
        verbose_name = 'Короткая ссылка'
        verbose_name_plural = 'Короткие ссылки'

    def __str__(self):
        return f"Короткая ссылка для {self.recipe.name}"


class BaseUserRecipe(models.Model):
    """
    Базовая модель для связей пользователя с рецептом.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        abstract = True
        unique_together = ('user', 'recipe')

    def __str__(self):
        return f'{self.user.username} добавил {self.recipe.name}'


class ShoppingCart(BaseUserRecipe):
    """
    Корзина пользователя.
    """
    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

    def __str__(self):
        return super().__str__() + ' в список покупок'


class FavoriteRecipe(BaseUserRecipe):
    """
    Избранные рецепты пользователя.
    """
    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return super().__str__() + ' в избранное'
