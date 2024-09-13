from django_filters import (FilterSet,
                            ModelMultipleChoiceFilter,
                            BooleanFilter, CharFilter)

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

    class Meta:
        model = Recipe
        fields = (
            'is_favorited', 'is_in_shopping_cart', 'author', 'tags'
        )

    def filter_user_list(self, queryset, name, value):
        """
        Фильтрация по спискам пользователя (избранное или список покупок).
        """
        if not self.request.user.is_authenticated:
            return queryset.none()
        user = self.request.user
        field_mapping = {
            'is_favorited': 'favorites',
            'is_in_shopping_cart': 'shoppingcart'
        }
        if name in field_mapping and value:
            related_field = field_mapping[name]
            return queryset.filter(**{related_field + '__user': user})
        return queryset


class IngredientFilter(FilterSet):
    """
    Фильтрация ингредиентов.
    """
    name = CharFilter(lookup_expr='istartswith',)

    class Meta:
        model = Ingredient
        fields = ('name',)
