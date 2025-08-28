import logging
import random
import time
import sqlite3
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (замените на ваш)
BOT_TOKEN = "8062907219:AAFxc2UD7J0Cw9f9oGOIOIQcqmrlmq12Aqg"

# Списки для случайных вариантов
COFFEE_TYPES = [
    "с булочкой с маком",
    "с овсяным печеньем",
    "с пряником",
    "с шоколадным кексом",
    "с ванильным круассаном",
    "с миндальным печеньем"
]

SPILL_MESSAGES = [
    "ой, неловко получилось",
    "какая неудача",
    "руки-крюки",
    "сегодня не твой день",
    "кофе решил сбежать"
]


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('maccoffee.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        total_coffee REAL DEFAULT 0,
        last_drink_time INTEGER DEFAULT 0
    )
    ''')

    conn.commit()
    conn.close()


def get_user_info(user_id):
    conn = sqlite3.connect('maccoffee.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    conn.close()
    return user


def update_user_info(user_id, username, first_name, last_name, coffee_amount):
    conn = sqlite3.connect('maccoffee.db')
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = cursor.fetchone()

    current_time = int(time.time())

    if user:
        new_total = user[4] + coffee_amount
        cursor.execute('''
        UPDATE users 
        SET username = ?, first_name = ?, last_name = ?, total_coffee = ?, last_drink_time = ?
        WHERE user_id = ?
        ''', (username, first_name, last_name, new_total, current_time, user_id))
    else:
        cursor.execute('''
        INSERT INTO users (user_id, username, first_name, last_name, total_coffee, last_drink_time)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, coffee_amount, current_time))

    conn.commit()
    conn.close()
    return new_total if user else coffee_amount


def can_drink_coffee(user_id):
    conn = sqlite3.connect('maccoffee.db')
    cursor = conn.cursor()

    cursor.execute('SELECT last_drink_time FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    conn.close()

    if not result or not result[0]:
        return True, 0

    last_drink_time = result[0]
    current_time = int(time.time())
    time_diff = current_time - last_drink_time

    if time_diff >= 3600:
        return True, 0
    else:
        wait_time = 3600 - time_diff
        return False, wait_time


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_text = f"Привет, {user.first_name}! ☕\n\nЯ бот для отслеживания потребления маккофе!\n\n"
    welcome_text += "Используй команду /maccoffee или напиши 'Випити маккофе' чтобы выпить кофе!\n"
    welcome_text += "Также доступна команда /stats для просмотра статистики."

    keyboard = [['Випити маккофе', '/stats']]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def maccoffee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name

    can_drink, wait_time = can_drink_coffee(user_id)

    if not can_drink:
        minutes = wait_time // 60
        seconds = wait_time % 60

        response_text = f"{username}, ты недавно пил(а) маккофе, попробуй через {minutes} минут {seconds} секунд"

        user_info = get_user_info(user_id)
        if user_info:
            total_coffee = user_info[4]
            response_text += f"\n\nВыпито всего: {total_coffee:.1f} л. 🍵"

        await update.message.reply_text(response_text)
        return

    # Визначаємо різні об'єми маккофе: 0.5, 1.0, 1.5, 2.0 літра
    coffee_options = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0]
    coffee_amount = random.choice(coffee_options)

    # 15% шанс пролить каву (від'ємне значення)
    if random.random() < 0.15:
        spill_amount = random.choice([-0.5, -1.0, -1.5, -2.0, -2.5, -3.0, -3.5, 4.0])
        spill_message = random.choice(SPILL_MESSAGES)
        
        if spill_amount == -0.5:
            message = f"❌ {username}, {spill_message} і пролив(ла) 0.5 літра маккофе! 😢"
        else:
            message = f"❌ {username}, {spill_message} і пролив(ла) {abs(spill_amount):.1f} літри маккофе! 😢"
        
        # Оновлюємо інформацію в базі даних
        new_total = update_user_info(user_id, user.username, user.first_name, user.last_name, spill_amount)
        
        message += f"\n\nВипито всього: {new_total:.1f} л. ☕"
        
        await update.message.reply_text(message)
        return

    # Якщо каву не пролили
    coffee_type = random.choice(COFFEE_TYPES)
    
    if coffee_amount == 0.5:
        message = f"✅ {username}, випив(ла) 0.5 літра маккофе {coffee_type}! ☕"
    elif coffee_amount == 1.0:
        message = f"✅ {username}, випив(ла) 1 літр маккофе {coffee_type}! ☕"
    else:
        message = f"✅ {username}, випив(ла) {coffee_amount:.1f} літри маккофе {coffee_type}! ☕"

    # Оновлюємо інформацію в базі даних
    new_total = update_user_info(user_id, user.username, user.first_name, user.last_name, coffee_amount)

    message += f"\n\nВипито всього: {new_total:.1f} л. ☕"

    await update.message.reply_text(message)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    username = f"@{user.username}" if user.username else user.first_name

    user_info = get_user_info(user_id)

    if user_info:
        total_coffee = user_info[4]
        response_text = f"📊 Статистика для {username}:\n"
        response_text += f"Випито всього: {total_coffee:.1f} л. маккофе ☕\n\n"

        conn = sqlite3.connect('maccoffee.db')
        cursor = conn.cursor()
        cursor.execute('SELECT username, first_name, total_coffee FROM users ORDER BY total_coffee DESC LIMIT 5')
        top_users = cursor.fetchall()
        conn.close()

        response_text += "🏆 Топ-5 кавоманів:\n"
        for i, (db_username, first_name, total) in enumerate(top_users, 1):
            display_name = f"@{db_username}" if db_username else first_name
            response_text += f"{i}. {display_name}: {total:.1f} л.\n"

    else:
        response_text = f"{username}, ти ще не пив(ла) маккофе! Використовуй /maccoffee щоб почати!"

    await update.message.reply_text(response_text)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower().strip()
    
    # Тільки точні збіги без зайвих пробілів
    exact_commands = ['випити маккофе', 'випити маккофе', 'выпить маккофе', 'маккофе']
    
    if text in exact_commands:
        await maccoffee(update, context)
    # else: НІЧОГО НЕ РОБИМО - ігноруємо інші повідомлення


def main():
    init_db()

    # Створюємо додаток
    application = Application.builder().token(BOT_TOKEN).build()

    # Додаємо обробники - ТІЛЬКИ КОМАНДИ
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("maccoffee", maccoffee))
    application.add_handler(CommandHandler("stats", stats))
    
    # Обробник тексту ТІЛЬКИ для точних команд
    application.add_handler(MessageHandler(
        filters.Regex(r'^(випити маккофе|выпить маккофе|маккофе)$'),
        handle_message
    ))

    # Запускаємо бота
    print("Бот запущений...")
    application.run_polling()


if __name__ == "__main__":
    main()

