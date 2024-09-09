from django.contrib import admin

from recipes.models import (
    Tag,
    Recipe,
    ShortLink,
    FavoriteRecipe,
    Ingredient,
    ShoppingCart,
    IngredientRecipeAmountModel,
    TagRecipe,
)


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    ordering = ('name',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    ordering = ('name',)


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author_username', 'image_tag', 'favorites_count'
    )
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags',)
    ordering = ('-id',)

    @admin.display(ordering='author__username')
    def author_username(self, obj):
        return obj.author.username

    @admin.display(ordering='favorites__count')
    def favorites_count(self, obj):
        return obj.favorites.count()

    class Meta:
        model = Recipe


class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'link')
    search_fields = ('recipe__name', 'link',)


class IngredientRecipeAmountModelAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount')


class TagRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'tag', 'recipe')


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')


class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')


admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShortLink, ShortLinkAdmin)
admin.site.register(FavoriteRecipe, FavoriteRecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(
    IngredientRecipeAmountModel,
    IngredientRecipeAmountModelAdmin
)
admin.site.register(TagRecipe, TagRecipeAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
