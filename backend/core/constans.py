MAX_EMAIL: int = 254
MAX_NAME: int = 150
MAX_TAG: int = 32
MAX_INGREDIENT: int = 128
MAX_UNIT: int = 64
RECIPE_MAX_FIELDS: int = 256
BASE_DOMAIN: str = "https://foodgram.example.org"
SHORT_LINK_LENGTH: int = 3
PAGE_SIZE: int = 6
TOKEN_LENGTH: int = 32
MAX_ROLE_LENGTH: int = 20
ROLE_CHOICES: dict = {
    'user': 'user',
    'admin': 'admin',
}
ROLE_CHOICES_LIST: list = [(key, value) for key, value in ROLE_CHOICES.items()]
CSV_HEADERS: list = ['Ингредиент', 'Количество', 'Единица измерения']
FILE_BEGIN: int = 0
RECIPE_LIMIT: int = 2
URL_ID: int = 2
