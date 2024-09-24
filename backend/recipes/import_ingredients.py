from csv import DictReader

from django.conf import settings
from django.core.management import BaseCommand
from recipes.models import Ingredient

from core.constans import MIN_UNIT
DATA_DIR = settings.BASE_DIR / 'data'


class Command(BaseCommand):

    help = "Загружает ингредиенты в БД из csv"

    def handle(self, *args, **options):
        with open(
            DATA_DIR / 'ingredients.csv', encoding='utf-8'
        ) as ingredients:
            if Ingredient.objects.count() < MIN_UNIT:
                ingredients_to_load = []
                for row in DictReader(
                    ingredients, fieldnames=['name', 'measurement_unit']
                ):
                    ingredients_to_load.append(Ingredient(**row))
                Ingredient.objects.bulk_create(ingredients_to_load)
