import os
from dotenv import load_dotenv

# Загружаем переменные из .env файла
load_dotenv()

# Токен Telegram бота
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# API ключ для погоды
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY')

# URL для API погоды
WEATHER_API_URL = "http://api.openweathermap.org/data/2.5/weather"

# URL для API продуктов
FOOD_API_URL = "https://world.openfoodfacts.org/cgi/search.pl"
