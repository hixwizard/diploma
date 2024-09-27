from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from core.constans import MIN_AMOUNT
from recipes.models import (
    TagRecipe, ShoppingCart, FavoriteRecipe, IngredientRecipeAmountModel
)


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
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                ingredient = form.cleaned_data.get('ingredient')
                amount = form.cleaned_data.get('amount')
                if ingredient in ingredients:
                    raise ValidationError(
                        'Ингредиенты в рецепте не должны повторяться.')
                if amount is None or amount <= MIN_AMOUNT:
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


class ShoppingCartForm(forms.ModelForm):
    """
    Форма для добавления рецептов в корзину покупок.
    """
    class Meta:
        model = ShoppingCart
        fields = ['user', 'recipe']

    def clean(self):
        super().clean()
        user = self.cleaned_data.get('user')
        recipe = self.cleaned_data.get('recipe')
        if ShoppingCart.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError(
                'Этот рецепт уже добавлен в корзину покупок.')


class FavoriteRecipeForm(forms.ModelForm):
    """
    Форма для добавления рецептов в избранное.
    """
    class Meta:
        model = FavoriteRecipe
        fields = ['user', 'recipe']

    def clean(self):
        super().clean()
        user = self.cleaned_data.get('user')
        recipe = self.cleaned_data.get('recipe')
        if FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            raise ValidationError(
                'Этот рецепт уже добавлен в избранное.')
