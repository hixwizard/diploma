from django.db import models

from users.models import User
from core.constans import MAX_TAG, MAX_INGREDIENT, MAX_UNIT, RECIPE_MAX_FIELDS


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
        Tag,
        through='TagRecipe',
        verbose_name='Идентификаторы'
    )
    image = models.ImageField(
        upload_to='media/recipes/',
        blank=True,
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

    @property
    def image_tag(self):
        if self.image:
            return f'<img src="{self.image.url}" width="50" height="50" />'
        return 'Нет изображения'

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
        related_name='used_in_recipes',
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


class ShoppingCartItem(models.Model):
    """
    Промежуточная модель для элементов списка покупок.
    """
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    quantity = models.PositiveSmallIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Элемент списка покупок'
        verbose_name_plural = 'Элементы списка покупок'

    def __str__(self):
        return f'{self.quantity} x {self.recipe.name}'


class ShoppingCart(models.Model):
    """
    Корзина пользователя.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='in_shoppingcarts'
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Списки покупок'

    def __str__(self):
        return (f'{self.user.username} добавил'
                f'{self.recipe.name} в список покупок')


class FavoriteRecipe(models.Model):
    """
    Избранные рецепеты пользователя.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='favorites'
    )

    class Meta:
        verbose_name = 'Избранный рецепт'
        verbose_name_plural = 'Избранные рецепты'

    def __str__(self):
        return f'{self.user.username} добавил {self.recipe.name} в избраннное'
