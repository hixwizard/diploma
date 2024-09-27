from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, BaseModelFormSet

from core.constans import MIN_AMOUNT
from recipes.models import (IngredientRecipeAmountModel, TagRecipe,
                            ShoppingCart, FavoriteRecipe)


class IngredientRecipeAmountModelFormFormSet(BaseModelFormSet):
    """
    Валидация ингредиентов.
    """
    def __init__(self, *args, **kwargs):
        instance = kwargs.pop('instance', None)
        super().__init__(*args, **kwargs)
        self.instance = instance
        self.new_objects = []
        if self.instance is not None:
            self.queryset = IngredientRecipeAmountModel.objects.filter(
                recipe=self.instance
            )

    def save_new(self, form, commit=True):
        instance = super().save_new(form, commit)
        self.new_objects.append(instance)
        return instance

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
                has_ingredient = True
                if ingredient in ingredients:
                    raise ValidationError(
                        'Ингредиенты в рецепте должны быть уникальными.')
                if amount < MIN_AMOUNT:
                    raise ValidationError(
                        f'Количество должно быть больше {MIN_AMOUNT}.')
                ingredients.add(ingredient)
        if not has_ingredient:
            raise ValidationError(
                'Рецепт должен содержать хотя бы один ингредиент.')

    def save(self, commit=True):
        instances = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                ingredient = form.cleaned_data['ingredient']
                amount = form.cleaned_data['amount']
                recipe = self.instance
                instances.append(IngredientRecipeAmountModel(
                    recipe=recipe, ingredient=ingredient, amount=amount))
        if instances:
            IngredientRecipeAmountModel.objects.bulk_create(instances)
        return instances


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

    def save(self, commit=True):
        instances = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                tag = form.cleaned_data['tag']
                recipe = self.instance
                instances.append(TagRecipe(recipe=recipe, tag=tag))
        if instances:
            TagRecipe.objects.bulk_create(instances)
        return instances


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
