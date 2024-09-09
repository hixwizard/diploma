from django_filters import (
    FilterSet, ModelMultipleChoiceFilter,
    BooleanFilter, NumberFilter, CharFilter)

from recipes.models import Recipe, Tag, Ingredient


class RecipeFilter(FilterSet):
    """
    Фильтр рецептов.
    """
    tags = ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
    )
    is_favorited = BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = BooleanFilter(method='filter_is_in_shopping_cart')
    recipes_limit = NumberFilter(field_name='recipes')

    def filter_is_favorited(self, queryset, name, value):
        """
        Избранное.
        """
        request = self.request
        if not request.user.is_authenticated:
            return queryset.none()
        if value:
            return queryset.filter(favorites__user=request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """
        Список покупок.
        """
        request = self.request
        if not request.user.is_authenticated:
            return queryset.none()
        if value:
            return queryset.filter(shoppingcart__user=request.user)
        return queryset

    class Meta:
        model = Recipe
        fields = (
            'is_favorited', 'is_in_shopping_cart', 'author', 'tags'
        )


class IngredientFilter(FilterSet):
    """
    Фильтрация ингредиентов.
    """
    name = CharFilter(lookup_expr='istartswith',)

    class Meta:
        model = Ingredient
        fields = ('name',)
