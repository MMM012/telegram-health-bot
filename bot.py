"""
Telegram-бот для трекинга воды, калорий и тренировок
"""

import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
import requests
from config import TELEGRAM_TOKEN, WEATHER_API_KEY, WEATHER_API_URL

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище данных
users_data = {}

# Состояния для диалогов
WEIGHT, HEIGHT, AGE, ACTIVITY, CITY, GENDER = range(6)
FOOD_AMOUNT = 100

# Типы тренировок и калории
WORKOUT_CALORIES = {
    'бег': 10, 'ходьба': 4, 'плавание': 8, 'велосипед': 7, 'йога': 3,
    'силовая': 6, 'танцы': 5, 'футбол': 9, 'баскетбол': 8, 'теннис': 7,
}

# База популярных продуктов
COMMON_FOODS = {
    # Фрукты
    'банан': {'name': 'Банан', 'calories': 89},
    'яблоко': {'name': 'Яблоко', 'calories': 52},
    'апельсин': {'name': 'Апельсин', 'calories': 47},
    'груша': {'name': 'Груша', 'calories': 57},
    'виноград': {'name': 'Виноград', 'calories': 69},
    'киви': {'name': 'Киви', 'calories': 61},
    'манго': {'name': 'Манго', 'calories': 60},
    'ананас': {'name': 'Ананас', 'calories': 50},
    'арбуз': {'name': 'Арбуз', 'calories': 30},
    
    # Английские
    'banana': {'name': 'Banana', 'calories': 89},
    'bananas': {'name': 'Banana', 'calories': 89},
    'apple': {'name': 'Apple', 'calories': 52},
    'orange': {'name': 'Orange', 'calories': 47},
    
    # Овощи
    'помидор': {'name': 'Помидор', 'calories': 18},
    'огурец': {'name': 'Огурец', 'calories': 15},
    'морковь': {'name': 'Морковь', 'calories': 41},
    'картофель': {'name': 'Картофель', 'calories': 77},
    'капуста': {'name': 'Капуста', 'calories': 25},
    
    # Мясо
    'курица': {'name': 'Курица', 'calories': 165},
    'говядина': {'name': 'Говядина', 'calories': 250},
    'свинина': {'name': 'Свинина', 'calories': 242},
    
    # Молочка
    'молоко': {'name': 'Молоко', 'calories': 60},
    'кефир': {'name': 'Кефир', 'calories': 56},
    'йогурт': {'name': 'Йогурт', 'calories': 59},
    'творог': {'name': 'Творог', 'calories': 169},
    'сыр': {'name': 'Сыр', 'calories': 356},
    
    # Крупы
    'рис': {'name': 'Рис варёный', 'calories': 130},
    'гречка': {'name': 'Гречка варёная', 'calories': 123},
    'овсянка': {'name': 'Овсянка', 'calories': 68},
    'макароны': {'name': 'Макароны', 'calories': 158},
    
    # Другое
    'яйцо': {'name': 'Яйцо', 'calories': 155},
    'хлеб': {'name': 'Хлеб', 'calories': 265},
    'шоколад': {'name': 'Шоколад', 'calories': 546},
}

def get_main_keyboard():
    """Клавиатура с кнопками"""
    keyboard = [
        [KeyboardButton("💧 Записать воду"), KeyboardButton("🍴 Записать еду")],
        [KeyboardButton("🏃 Записать тренировку"), KeyboardButton("📊 Мой прогресс")],
        [KeyboardButton("⚙️ Настроить профиль"), KeyboardButton("❓ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_weather(city):
    """Получает температуру"""
    try:
        params = {'q': city, 'appid': WEATHER_API_KEY, 'units': 'metric', 'lang': 'ru'}
        response = requests.get(WEATHER_API_URL, params=params, timeout=5)
        if response.status_code == 200:
            return {'success': True, 'temperature': response.json()['main']['temp']}
    except Exception as e:
        logger.error(f"Ошибка погоды: {e}")
    return {'success': False, 'temperature': 20}

def calculate_water_goal(weight, activity_minutes, temperature):
    """Считаем норму воды"""
    base = weight * 30
    activity = (activity_minutes / 30) * 500
    temp = min(500 + (temperature - 25) * 50, 1000) if temperature > 25 else 0
    return int(base + activity + temp)

def calculate_calorie_goal(weight, height, age, gender, activity_minutes):
    """Считаем норму калорий"""
    bmr = 10 * weight + 6.25 * height - 5 * age
    bmr += 5 if gender.lower() in ['м', 'male', 'муж'] else -161
    return int(bmr + (activity_minutes / 30) * 150)

def get_food_info(product_name):
    """Ищет еду в базе или через API"""
    product_lower = product_name.lower().strip()
    
    # Проверяем локальную базу
    if product_lower in COMMON_FOODS:
        food = COMMON_FOODS[product_lower]
        return {'success': True, 'name': food['name'], 'calories': food['calories']}
    
    # Пробуем API
    try:
        url = "https://world.openfoodfacts.org/cgi/search.pl"
        params = {'search_terms': product_name, 'json': True, 'page_size': 1}
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            products = response.json().get('products', [])
            if products:
                p = products[0]
                calories = p.get('nutriments', {}).get('energy-kcal_100g', 0)
                if calories > 0:
                    return {
                        'success': True,
                        'name': p.get('product_name', product_name),
                        'calories': calories
                    }
    except Exception as e:
        logger.error(f"Ошибка API: {e}")
    
    # Ищем похожие
    similar = [key for key in COMMON_FOODS.keys() 
               if product_lower in key or key in product_lower]
    return {'success': False, 'similar': similar[:5]}

# КОМАНДЫ

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    await update.message.reply_text(
        f"👋 Привет, {update.effective_user.first_name}!\n\n"
        "Я помогу тебе следить за водой, едой и тренировками.\n"
        "Используй кнопки ниже! ⬇️",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /help"""
    await update.message.reply_text(
        "📖 Как пользоваться:\n\n"
        "1️⃣ Настрой профиль (⚙️)\n"
        "2️⃣ Записывай воду, еду, тренировки\n"
        "3️⃣ Смотри прогресс (📊)\n\n"
        "Команды:\n"
        "/log_water 500\n"
        "/log_food банан\n"
        "/log_workout бег 30\n"
        "/check_progress"
    )

# НАСТРОЙКА ПРОФИЛЯ

async def set_profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏃‍♂️ Настроим профиль!\n\nШаг 1/6: Введи вес (кг):")
    return WEIGHT

async def get_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text)
        if not (0 < weight <= 300):
            await update.message.reply_text("❌ Вес от 1 до 300 кг:")
            return WEIGHT
        
        user_id = update.effective_user.id
        if user_id not in users_data:
            users_data[user_id] = {}
        users_data[user_id]['weight'] = weight
        
        await update.message.reply_text(f"✅ Вес: {weight} кг\n\nШаг 2/6: Введи рост (см):")
        return HEIGHT
    except ValueError:
        await update.message.reply_text("❌ Введи число:")
        return WEIGHT

async def get_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        height = float(update.message.text)
        if not (0 < height <= 250):
            await update.message.reply_text("❌ Рост от 1 до 250 см:")
            return HEIGHT
        users_data[update.effective_user.id]['height'] = height
        await update.message.reply_text(f"✅ Рост: {height} см\n\nШаг 3/6: Введи возраст:")
        return AGE
    except ValueError:
        await update.message.reply_text("❌ Введи число:")
        return HEIGHT

async def get_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        age = int(update.message.text)
        if not (0 < age <= 120):
            await update.message.reply_text("❌ Возраст от 1 до 120:")
            return AGE
        users_data[update.effective_user.id]['age'] = age
        await update.message.reply_text(f"✅ Возраст: {age} лет\n\nШаг 4/6: Пол (М/Ж):")
        return GENDER
    except ValueError:
        await update.message.reply_text("❌ Введи число:")
        return AGE

async def get_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if text in ['м', 'муж', 'мужской', 'male', 'm']:
        gender = 'М'
    elif text in ['ж', 'жен', 'женский', 'female', 'f']:
        gender = 'Ж'
    else:
        await update.message.reply_text("❌ Введи М или Ж:")
        return GENDER
    users_data[update.effective_user.id]['gender'] = gender
    await update.message.reply_text(f"✅ Пол: {gender}\n\nШаг 5/6: Минут активности в день?")
    return ACTIVITY

async def get_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        activity = int(update.message.text)
        if not (0 <= activity <= 1440):
            await update.message.reply_text("❌ От 0 до 1440:")
            return ACTIVITY
        users_data[update.effective_user.id]['activity'] = activity
        await update.message.reply_text(
            f"✅ Активность: {activity} мин\n\nШаг 6/6: Город?\n(Например: Moscow)"
        )
        return CITY
    except ValueError:
        await update.message.reply_text("❌ Введи число:")
        return ACTIVITY
async def get_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    city = update.message.text.strip()
    users_data[user_id]['city'] = city
    
    # Уведомляем что проверяем погоду
    await update.message.reply_text(f"🔍 Проверяю актуальную погоду в {city}...")
    
    weather = get_weather(city)
    temp = weather['temperature']
    users_data[user_id]['temperature'] = temp
    
    data = users_data[user_id]
    water_goal = calculate_water_goal(data['weight'], data['activity'], temp)
    calorie_goal = calculate_calorie_goal(
        data['weight'], data['height'], data['age'], data['gender'], data['activity']
    )
    
    users_data[user_id].update({
        'water_goal': water_goal,
        'calorie_goal': calorie_goal,
        'logged_water': 0,
        'logged_calories': 0,
        'burned_calories': 0
    })
    
    # Статус получения погоды
    status = "✅" if weather['success'] else "⚠️ (по умолчанию)"
    
    # Умная рекомендация по погоде
    if temp > 25:
        weather_tip = f"\n🔥 Жарко! Норма воды увеличена из-за температуры"
    elif temp < 0:
        weather_tip = f"\n❄️ Холодно! Не забывай про тёплые напитки"
    else:
        weather_tip = ""
    
    await update.message.reply_text(
        f"🎉 Профиль настроен!\n\n"
        f"📊 Твои данные:\n"
        f"• Вес: {data['weight']} кг\n"
        f"• Рост: {data['height']} см\n"
        f"• Возраст: {data['age']} лет\n"
        f"• Пол: {data['gender']}\n"
        f"• Активность: {data['activity']} мин/день\n"
        f"• Город: {city}\n\n"
        f"🌡️ Актуальная температура: {temp:.1f}°C {status}{weather_tip}\n\n"
        f"🎯 Дневные нормы:\n"
        f"💧 Вода: {water_goal} мл\n"
        f"🔥 Калории: {calorie_goal} ккал\n\n"
        f"Используй кнопки ниже! 👇",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END
async def cancel_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отменяет настройку профиля"""
    await update.message.reply_text(
        "❌ Настройка профиля отменена\n\n"
        "Используй /set_profile когда будешь готов",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


# ЛОГИРОВАНИЕ ВОДЫ

async def log_water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_data or 'water_goal' not in users_data[user_id]:
        await update.message.reply_text("❌ Сначала настрой профиль")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Укажи количество:\n/log_water 500")
        return
    
    try:
        amount = int(context.args[0])
        if not (0 < amount <= 5000):
            await update.message.reply_text("❌ От 1 до 5000 мл")
            return
        
        users_data[user_id]['logged_water'] += amount
        total = users_data[user_id]['logged_water']
        goal = users_data[user_id]['water_goal']
        remaining = goal - total
        
        if remaining > 0:
            await update.message.reply_text(
                f"💧 Записано: {amount} мл\n\n"
                f"📊 Выпито: {total}/{goal} мл\n"
                f"Осталось: {remaining} мл"
            )
        else:
            await update.message.reply_text(
                f"💧 Записано: {amount} мл\n\n"
                f"🎉 Норма выполнена! ({total}/{goal} мл)"
            )
    except ValueError:
        await update.message.reply_text("❌ Введи число")

# ЛОГИРОВАНИЕ ЕДЫ

async def log_food_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_data or 'calorie_goal' not in users_data[user_id]:
        await update.message.reply_text("❌ Сначала настрой профиль")
        return ConversationHandler.END
    
    if not context.args:
        await update.message.reply_text("❌ Укажи продукт:\n/log_food банан")
        return ConversationHandler.END
    
    product = ' '.join(context.args)
    await update.message.reply_text(f"🔍 Ищу: {product}...")
    
    food = get_food_info(product)
    
    if not food['success']:
        similar = food.get('similar', [])
        if similar:
            await update.message.reply_text(
                f"❌ Не нашёл '{product}'\n\n"
                f"Может быть:\n" + "\n".join(f"• {s}" for s in similar)
            )
        else:
            await update.message.reply_text(
                f"❌ Не нашёл '{product}'\n\n"
                "Попробуй:\n• банан, яблоко, курица, рис"
            )
        return ConversationHandler.END
    
    context.user_data['current_food'] = food
    await update.message.reply_text(
        f"✅ {food['name']}\n"
        f"📊 {food['calories']} ккал на 100 г\n\n"
        f"Сколько грамм?"
    )
    return FOOD_AMOUNT

async def get_food_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text)
        if not (0 < amount <= 10000):
            await update.message.reply_text("❌ От 1 до 10000 г:")
            return FOOD_AMOUNT
        
        food = context.user_data['current_food']
        calories = (food['calories'] / 100) * amount
        
        user_id = update.effective_user.id
        users_data[user_id]['logged_calories'] += calories
        
        total = users_data[user_id]['logged_calories']
        burned = users_data[user_id]['burned_calories']
        goal = users_data[user_id]['calorie_goal']
        
        await update.message.reply_text(
            f"✅ {food['name']} — {amount} г\n"
            f"🔥 +{calories:.0f} ккал\n\n"
            f"📊 Баланс:\n"
            f"• Потреблено: {total:.0f} ккал\n"
            f"• Сожжено: {burned:.0f} ккал\n"
            f"• Баланс: {total - burned:.0f} ккал\n"
            f"• Цель: {goal} ккал"
        )
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ Введи число:")
        return FOOD_AMOUNT

async def cancel_food(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено")
    return ConversationHandler.END

# ЛОГИРОВАНИЕ ТРЕНИРОВОК

async def log_workout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_data or 'calorie_goal' not in users_data[user_id]:
        await update.message.reply_text("❌ Сначала настрой профиль")
        return
    
    if not context.args or len(context.args) < 2:
        types = ', '.join(WORKOUT_CALORIES.keys())
        await update.message.reply_text(
            f"❌ Формат: /log_workout тип минуты\n"
            f"Пример: /log_workout бег 30\n\n"
            f"Типы: {types}"
        )
        return
    
    try:
        workout_type = context.args[0].lower()
        duration = int(context.args[1])
        
        if not (0 < duration <= 600):
            await update.message.reply_text("❌ От 1 до 600 минут")
            return
        
        cal_per_min = WORKOUT_CALORIES.get(workout_type, 6)
        weight = users_data[user_id]['weight']
        burned = cal_per_min * duration * (weight / 70)
        extra_water = int((duration / 30) * 200)
        
        users_data[user_id]['burned_calories'] += burned
        users_data[user_id]['water_goal'] += extra_water
        
        await update.message.reply_text(
            f"🏃‍♂️ {workout_type.capitalize()} — {duration} мин\n"
            f"🔥 Сожжено: {burned:.0f} ккал\n"
            f"💧 Выпей ещё: {extra_water} мл\n\n"
            f"📊 Всего сожжено: {users_data[user_id]['burned_calories']:.0f} ккал"
        )
    except ValueError:
        await update.message.reply_text("❌ Неверный формат")

# ПРОГРЕСС

async def check_progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in users_data or 'water_goal' not in users_data[user_id]:
        await update.message.reply_text("❌ Сначала настрой профиль")
        return
    
    data = users_data[user_id]
    water_logged = data['logged_water']
    water_goal = data['water_goal']
    water_percent = int((water_logged / water_goal) * 100) if water_goal > 0 else 0
    
    cal_consumed = data['logged_calories']
    cal_burned = data['burned_calories']
    cal_goal = data['calorie_goal']
    cal_balance = cal_consumed - cal_burned
    cal_percent = int((cal_balance / cal_goal) * 100) if cal_goal > 0 else 0
    
    water_bar = "🟦" * min(int(water_percent / 10), 10) + "⬜" * max(0, 10 - int(water_percent / 10))
    cal_bar = "🟧" * min(int(cal_percent / 10), 10) + "⬜" * max(0, 10 - int(cal_percent / 10))
    
    await update.message.reply_text(
        f"📊 Прогресс\n\n"
        f"💧 Вода:\n"
        f"{water_bar} {water_percent}%\n"
        f"Выпито: {water_logged}/{water_goal} мл\n\n"
        f"🔥 Калории:\n"
        f"{cal_bar} {cal_percent}%\n"
        f"Потреблено: {cal_consumed:.0f} ккал\n"
        f"Сожжено: {cal_burned:.0f} ккал\n"
        f"Баланс: {cal_balance:.0f}/{cal_goal} ккал\n\n"
        f"💪 Продолжай!"
    )

# ОБРАБОТЧИКИ КНОПОК

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💧 Записать воду":
        await update.message.reply_text("💧 Введи мл:\nНапример: 500")
        context.user_data['waiting_for'] = 'water'
    elif text == "🍴 Записать еду":
        await update.message.reply_text("🍴 Введи продукт:\nНапример: банан")
        context.user_data['waiting_for'] = 'food'
    elif text == "🏃 Записать тренировку":
        types = ', '.join(WORKOUT_CALORIES.keys())
        await update.message.reply_text(f"🏃 Введи тип и минуты:\nНапример: бег 30\n\nТипы: {types}")
        context.user_data['waiting_for'] = 'workout'
    elif text == "📊 Мой прогресс":
        await check_progress(update, context)
    elif text == "⚙️ Настроить профиль":
        await set_profile_start(update, context)
        return WEIGHT
    elif text == "❓ Помощь":
        await help_command(update, context)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    waiting = context.user_data.get('waiting_for')
    
    if waiting == 'water':
        try:
            context.args = [text]
            await log_water(update, context)
            context.user_data['waiting_for'] = None
        except:
            await update.message.reply_text("❌ Введи число")
    elif waiting == 'food':
        context.args = text.split()
        await log_food_start(update, context)
        context.user_data['waiting_for'] = None
        return FOOD_AMOUNT
    elif waiting == 'workout':
        parts = text.split()
        if len(parts) >= 2:
            context.args = parts
            await log_workout(update, context)
            context.user_data['waiting_for'] = None
        else:
            await update.message.reply_text("❌ Формат: тип минуты")
    else:
        await update.message.reply_text("Используй кнопки", reply_markup=get_main_keyboard())

# ОБРАБОТЧИКИ КНОПОК

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "💧 Записать воду":
        await update.message.reply_text("💧 Введи мл:\nНапример: 500")
        context.user_data['waiting_for'] = 'water'
    elif text == "🍴 Записать еду":
        await update.message.reply_text("🍴 Введи продукт:\nНапример: банан")
        context.user_data['waiting_for'] = 'food'
    elif text == "🏃 Записать тренировку":
        types = ', '.join(WORKOUT_CALORIES.keys())
        await update.message.reply_text(f"🏃 Введи тип и минуты:\nНапример: бег 30\n\nТипы: {types}")
        context.user_data['waiting_for'] = 'workout'
    elif text == "📊 Мой прогресс":
        await check_progress(update, context)
    elif text == "⚙️ Настроить профиль":
        await set_profile_start(update, context)
        return WEIGHT
    elif text == "❓ Помощь":
        await help_command(update, context)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обрабатывает текстовый ввод от кнопок"""
    text = update.message.text
    waiting = context.user_data.get('waiting_for')
    user_id = update.effective_user.id
    
    if waiting == 'water':
        try:
            amount = int(text)
            if not (0 < amount <= 5000):
                await update.message.reply_text("❌ От 1 до 5000 мл")
                return
            
            users_data[user_id]['logged_water'] += amount
            total = users_data[user_id]['logged_water']
            goal = users_data[user_id]['water_goal']
            remaining = goal - total
            
            if remaining > 0:
                await update.message.reply_text(
                    f"💧 Записано: {amount} мл\n\n"
                    f"📊 Выпито: {total}/{goal} мл\n"
                    f"Осталось: {remaining} мл"
                )
            else:
                await update.message.reply_text(
                    f"💧 Записано: {amount} мл\n\n"
                    f"🎉 Норма выполнена! ({total}/{goal} мл)"
                )
            context.user_data['waiting_for'] = None
        except ValueError:
            await update.message.reply_text("❌ Введи число")
            
    elif waiting == 'food':
        product = text.strip()
        await update.message.reply_text(f"🔍 Ищу: {product}...")
        
        food = get_food_info(product)
        
        if not food['success']:
            similar = food.get('similar', [])
            if similar:
                await update.message.reply_text(
                    f"❌ Не нашёл '{product}'\n\n"
                    f"Может быть:\n" + "\n".join(f"• {s}" for s in similar)
                )
            else:
                await update.message.reply_text(
                    f"❌ Не нашёл '{product}'\n\n"
                    "Попробуй:\n• банан, яблоко, курица, рис"
                )
            context.user_data['waiting_for'] = None
            return
        
        context.user_data['current_food'] = food
        context.user_data['waiting_for'] = 'food_amount'
        await update.message.reply_text(
            f"✅ {food['name']}\n"
            f"📊 {food['calories']} ккал на 100 г\n\n"
            f"Сколько грамм?"
        )
        
    elif waiting == 'food_amount':
        try:
            amount = float(text)
            if not (0 < amount <= 10000):
                await update.message.reply_text("❌ От 1 до 10000 г:")
                return
            
            food = context.user_data['current_food']
            calories = (food['calories'] / 100) * amount
            
            users_data[user_id]['logged_calories'] += calories
            total = users_data[user_id]['logged_calories']
            burned = users_data[user_id]['burned_calories']
            goal = users_data[user_id]['calorie_goal']
            
            await update.message.reply_text(
                f"✅ {food['name']} — {amount} г\n"
                f"🔥 +{calories:.0f} ккал\n\n"
                f"📊 Баланс:\n"
                f"• Потреблено: {total:.0f} ккал\n"
                f"• Сожжено: {burned:.0f} ккал\n"
                f"• Баланс: {total - burned:.0f} ккал\n"
                f"• Цель: {goal} ккал"
            )
            
            context.user_data['waiting_for'] = None
            context.user_data['current_food'] = None
        except ValueError:
            await update.message.reply_text("❌ Введи число:")
            
    elif waiting == 'workout':
        parts = text.split()
        if len(parts) >= 2:
            try:
                workout_type = parts[0].lower()
                duration = int(parts[1])
                
                if not (0 < duration <= 600):
                    await update.message.reply_text("❌ От 1 до 600 минут")
                    return
                
                cal_per_min = WORKOUT_CALORIES.get(workout_type, 6)
                weight = users_data[user_id]['weight']
                burned = cal_per_min * duration * (weight / 70)
                extra_water = int((duration / 30) * 200)
                
                users_data[user_id]['burned_calories'] += burned
                users_data[user_id]['water_goal'] += extra_water
                
                await update.message.reply_text(
                    f"🏃‍♂️ {workout_type.capitalize()} — {duration} мин\n"
                    f"🔥 Сожжено: {burned:.0f} ккал\n"
                    f"💧 Выпей ещё: {extra_water} мл\n\n"
                    f"📊 Всего сожжено: {users_data[user_id]['burned_calories']:.0f} ккал"
                )
                context.user_data['waiting_for'] = None
            except ValueError:
                await update.message.reply_text("❌ Формат: тип минуты")
        else:
            await update.message.reply_text("❌ Формат: тип минуты")
    else:
        await update.message.reply_text("Используй кнопки", reply_markup=get_main_keyboard())

# ГЛАВНАЯ ФУНКЦИЯ

def main():
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    profile_conv = ConversationHandler(
        entry_points=[
            CommandHandler('set_profile', set_profile_start),
            MessageHandler(filters.Regex("^⚙️ Настроить профиль$"), handle_buttons)
        ],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_weight)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_height)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_gender)],
            ACTIVITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_activity)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_city)],
        },
        fallbacks=[CommandHandler('cancel', cancel_profile)],
        allow_reentry=True
    )
    
    food_conv = ConversationHandler(
        entry_points=[CommandHandler('log_food', log_food_start)],
        states={FOOD_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_food_amount)]},
        fallbacks=[CommandHandler('cancel', cancel_food)],
        allow_reentry=True
    )
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("log_water", log_water))
    application.add_handler(CommandHandler("log_workout", log_workout))
    application.add_handler(CommandHandler("check_progress", check_progress))
    application.add_handler(MessageHandler(
        filters.Regex("^(💧 Записать воду|🍴 Записать еду|🏃 Записать тренировку|📊 Мой прогресс|❓ Помощь)$"),
        handle_buttons
    ))
    application.add_handler(profile_conv)
    application.add_handler(food_conv)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()

