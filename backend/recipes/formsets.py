from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet

from recipes.models import (IngredientRecipeAmountModel, TagRecipe,
                            ShoppingCart, FavoriteRecipe)


class IngredientRecipeAmountInlineFormSet(BaseInlineFormSet):
    """
    Валидация ингредиентов.
    """
    def clean(self):
        """
        Проверка наличия хотя бы одного ингредиента
        и уникальности ингредиентов в рецепте.
        """
        super().clean()

        if any(self.errors):
            return

        ingredients = set()
        self.cleaned_ingredients = []
        has_ingredient = False

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                ingredient = form.cleaned_data.get('ingredient')
                has_ingredient = True
                if ingredient in ingredients:
                    raise ValidationError(
                        'Ингредиенты в рецепте должны быть уникальными.'
                    )
                ingredients.add(ingredient)
                self.cleaned_ingredients.append(form.cleaned_data)
        if not has_ingredient:
            raise ValidationError(
                'Рецепт должен содержать хотя бы один ингредиент.'
            )

    def save(self, commit=True):
        """
        Сохраняем ингредиенты с помощью bulk_create.
        """
        instances = []
        for cleaned_data in self.cleaned_ingredients:
            ingredient = cleaned_data['ingredient']
            amount = cleaned_data['amount']
            recipe = self.instance
            instances.append(IngredientRecipeAmountModel(
                recipe=recipe,
                ingredient=ingredient,
                amount=amount
            ))
        if instances:
            IngredientRecipeAmountModel.objects.bulk_create(instances)
        return instances


class TagRecipeInlineFormSet(BaseInlineFormSet):
    """
    Валидация тегов.
    """
    def clean(self):
        """
        Проверка наличия хотя бы одного тега и уникальности тегов в рецепте.
        """
        super().clean()

        if any(self.errors):
            return

        tags = set()
        self.cleaned_tags = []
        has_tag = False

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get(
                'DELETE', False
            ):
                tag = form.cleaned_data.get('tag')
                has_tag = True
                if tag in tags:
                    raise ValidationError(
                        'Теги в рецепте не должны повторяться.'
                    )
                tags.add(tag)
                self.cleaned_tags.append(form.cleaned_data)
        if not has_tag:
            raise ValidationError(
                'Рецепт должен содержать хотя бы один тег.'
            )

    def save(self, commit=True):
        """
        Сохраняем теги с помощью bulk_create.
        """
        instances = []
        for cleaned_data in self.cleaned_tags:
            tag = cleaned_data['tag']
            recipe = self.instance
            instances.append(TagRecipe(
                recipe=recipe,
                tag=tag
            ))
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
