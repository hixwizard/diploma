from django.contrib import admin
from django.utils.safestring import mark_safe
from recipes.models import (
    Tag,
    Recipe,
    ShortLink,
    FavoriteRecipe,
    Ingredient,
    ShoppingCart,
    IngredientRecipeAmountModel,
    TagRecipe
)


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    ordering = ('name',)


class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    ordering = ('name',)


class IngredientRecipeAmountInline(admin.TabularInline):
    model = IngredientRecipeAmountModel
    extra = 1


class TagRecipeInline(admin.TabularInline):
    model = TagRecipe
    extra = 1


class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'name', 'author_username', 'image_tag'
    )
    search_fields = ('name', 'author__username', 'author__email')
    list_filter = ('tags',)
    ordering = ('-id',)
    inlines = [IngredientRecipeAmountInline, TagRecipeInline]
    filter_horizontal = ('tags',)

    def author_username(self, obj):
        return obj.author.username

    def favorites_count(self, obj):
        return obj.favorites.count()

    def image_tag(self, obj):
        if obj.image:
            return mark_safe('<img src="{}" width="150"'
                             'height="100" />'.format(obj.image.url))
        return None

    class Meta:
        model = Recipe


class ShortLinkAdmin(admin.ModelAdmin):
    list_display = ('recipe', 'link')
    search_fields = ('recipe__name', 'link',)


class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')


class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')


admin.site.register(Tag, TagAdmin)
admin.site.register(Recipe, RecipeAdmin)
admin.site.register(ShortLink, ShortLinkAdmin)
admin.site.register(FavoriteRecipe, FavoriteRecipeAdmin)
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(ShoppingCart, ShoppingCartAdmin)
