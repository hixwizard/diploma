from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from core.constans import MIN_AMOUNT
from recipes.models import ShoppingCart, FavoriteRecipe


class IngredientRecipeInlineFormSet(BaseInlineFormSet):
    """
    Валидация ингредиентов.
    """
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        ingredients = set()
        has_ingredient = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                ingredient = form.cleaned_data.get('ingredient')
                amount = form.cleaned_data.get('amount')
                if ingredient in ingredients:
                    raise ValidationError(
                        'Ингредиенты в рецепте не должны повторяться.')
                if amount is None or amount < MIN_AMOUNT:
                    raise ValidationError(
                        'Количество должно быть положительным числом.')
                has_ingredient = True
                ingredients.add(ingredient)
        if not has_ingredient:
            raise ValidationError(
                'Рецепт должен содержать хотя бы один ингредиент.')


class TagRecipeInlineFormSet(BaseInlineFormSet):
    """
    Валидация тегов.
    """
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        tags = set()
        has_tag = False
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                tag = form.cleaned_data.get('tag')
                has_tag = True
                if tag in tags:
                    raise ValidationError(
                        'Теги в рецепте не должны повторяться.')
                tags.add(tag)
        if not has_tag:
            raise ValidationError('Рецепт должен содержать хотя бы один тег.')


class BaseUserRecipeForm(forms.ModelForm):
    """
    Базовая форма для добавления рецептов в связи с пользователем
    (например, в корзину покупок или в избранное).
    """
    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        self.model_class = kwargs.pop('model_class')
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()
        user = self.cleaned_data.get('user')
        recipe = self.cleaned_data.get('recipe')
        if self.model_class.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError(
                f'Этот рецепт уже добавлен в '
                f'{self.model_class._meta.verbose_name}.'
            )


class ShoppingCartForm(BaseUserRecipeForm):
    """
    Форма для добавления рецептов в корзину покупок.
    """
    class Meta:
        model = ShoppingCart
        fields = ['user', 'recipe']

    def __init__(self, *args, **kwargs):
        kwargs['model_class'] = ShoppingCart
        super().__init__(*args, **kwargs)


class FavoriteRecipeForm(BaseUserRecipeForm):
    """
    Форма для добавления рецептов в избранное.
    """
    class Meta:
        model = FavoriteRecipe
        fields = ['user', 'recipe']

    def __init__(self, *args, **kwargs):
        kwargs['model_class'] = FavoriteRecipe
        super().__init__(*args, **kwargs)
