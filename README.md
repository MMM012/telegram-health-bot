Telegram-бот для трекинга воды, калорий и тренировок с интеграцией погоды.

Основные обработчики (Handlers):
start() - команда /start, приветствие и показ главной клавиатуры

help_command() - команда /help, инструкция по использованию

check_progress() - команда /check_progress, показывает статистику воды и калорий с прогресс-барами

Настройка профиля (6 шагов):
set_profile_start() - начало настройки

get_weight() - получение веса (кг)

get_height() - получение роста (см)

get_age() - получение возраста

get_gender() - получение пола (М/Ж)

get_activity() - получение минут активности в день

get_city() - получение города для погоды

cancel_profile() - отмена настройки

Трекинг воды:
log_water() - запись потребления воды (мл)

Трекинг еды:
log_food_start() - поиск продукта по названию

get_food_amount() - запись количества еды (граммы)

get_food_info() - поиск калорий продукта (локальная база + Open Food Facts API)

cancel_food() - отмена записи

Трекинг тренировок:
log_workout() - запись тренировки (тип + минуты)

Вспомогательные функции:
get_weather() - получение температуры через OpenWeather API

calculate_water_goal() - расчёт дневной нормы воды с учётом веса, активности, температуры

calculate_calorie_goal() - расчёт дневной нормы калорий 

get_main_keyboard() - создание клавиатуры с кнопками

handle_buttons() - обработчик нажатий на кнопки

handle_text_input() - обработчик текстового ввода

Базы данных:
WORKOUT_CALORIES - калории для 10 типов тренировок 

COMMON_FOODS - 40+ популярных продуктов с калориями

Интеграции API:
Telegram Bot API - через библиотеку python-telegram-bot

OpenWeather API - получение температуры для расчёта нормы воды


Исходный код: GitHub репозиторий MMM012/telegram-health-bot

Ссылка: https://github.com/MMM012/telegram-health-bot

Скриншоты: Папка screenshots/ в репозитории 

Развёрнутый бот: Render.com (облачная платформа)

URL: https://telegram-health-bot-3pse.onrender.com