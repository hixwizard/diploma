from django.urls import path, include
from rest_framework.routers import DefaultRouter

from api.views import (UserViewSet, TagViewSet,
                       RecipeViewSet, IngredientViewSet)

router_v1 = DefaultRouter()

router_v1.register(r'tags', TagViewSet, basename='tags')
router_v1.register(r'users', UserViewSet, basename='users')
router_v1.register(r'recipes', RecipeViewSet, basename='recipes')
router_v1.register(r'ingredients', IngredientViewSet, basename='ingredients')

urlpatterns = [
    path('api/auth/', include('djoser.urls.authtoken')),
    path('api/', include(router_v1.urls)),
]
