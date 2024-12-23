import sqlite3
from aiogram import types, Router, Bot, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, FSInputFile
import random
from config import TOKEN, BOT_NAME, X, O
import traceback
from Games import XO
import datetime
from datetime import datetime, timedelta, date
import asyncio


bot = Bot(token=TOKEN)
router = Router()

# Список забанених та замучених користувачів
banned_users = set()
muted_users = {}

son = [
    "сину", "сина", "синочок", "хіро",
    "hero", "son", "myson", "child", "kiddo", "junior"
]

# Ініціалізація бази даних
with sqlite3.connect("DataBases/warns.db") as conn:
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY,
        first_name TEXT,
        last_name TEXT,
        bio TEXT DEFAULT '',
        profile_photo_id TEXT DEFAULT ''
    )
    """)

commands_dict = {
    "Зміна акаунту": [
        "👤 /profile - Переглянути свій профіль",
        "🏞 /set_photo - Змінити фото профілю",
        "🔵 /set_bio - Додати або змінити біографію",
        "🔵 /change_nickname - Змінити нікнейм",
        "👤 /whois - Дізнатися інформацію про користувача за ID або username."
    ],
    "Адміністрування": [
        "🚫 /ban - Забанити користувача",
        "✅ /unban - Розбанити користувача",
        "🚫 /mute - Замутити користувача",
        "✅ /unmute - Розмутити користувача",
        "⚠️ /warn - Дати попередження",
        "❌ /kick - Кікнути користувача",
        "🗣 /report - Показати всіх адміністраторів"
    ],
    "Виховання": [
        "🤜 /beat_with_belt - Побити одоробло"
    ],
    "Відносини": [
        "❤️ !!відносини - Розпочати глобальні відносини.",
        "💔 !!розлучитись - Завершити глобальні відносини.",
        "💑 !відносини - Розпочати локальні відносини у чаті.",
        "👋 !розлучитись - Завершити локальні відносини у чаті.",
        "👰‍♂️ !шлюби - Переглянути свої глобальні відносини.",
        "👑 !топшлюбів - Переглянути топ локальних шлюбів чату."
    ],
    "Інше": [
        "❓ /help - Показати список команд",
        "🔵 /start - Запустити бота",
        "📜 /stats - Переглянути статистику повідомлень",
        "🎄 /christmas - Запустити таймер до Нового року.",
        "🌳 /create_tree - Створити новорічне дерево у своєму профілі.",
        "🎮 /xo - Запустити гру \"Хрестики-нулики\"."
    ],
    "Інтерактивне": [
        "👍 + - Додати репутацію іншому користувачеві."
    ]
}

# Трекер для активних таймерів
active_timers = {}


# Створення або відкриття бази даних
def create_connection():
    return sqlite3.connect('DataBases/history.db')

# Функція для створення таблиці повідомлень
def create_messages_table():
    with create_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                text TEXT UNIQUE
            )
        ''')

# Збереження текстового повідомлення до бази даних, уникаючи повторення фраз
def save_message_to_file(text):
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            # Перевірка наявності дубліката
            cursor.execute('SELECT COUNT(*) FROM messages WHERE text = ?', (text,))
            count = cursor.fetchone()[0]
            if count == 0:
                # Вставка нового повідомлення, якщо дубліката немає
                cursor.execute('''
                    INSERT OR IGNORE INTO messages (text)
                    VALUES (?)
                ''', (text,))
    except sqlite3.Error as e:
        print(f"Error saving message: {e}")

# Зчитування випадкового повідомлення з бази даних
def get_random_message():
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT text FROM messages ORDER BY RANDOM() LIMIT 1')
            result = cursor.fetchone()
            return result[0] if result else None
    except sqlite3.Error as e:
        print(f"Error retrieving message: {e}")
        return None

# Створення таблиці при першому запуску
create_messages_table()

# Функція перевірки, чи є користувач адміністратором
async def is_admin(bot: Bot, chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]

# Перевіряємо, чи є цільовий користувач адміністратором або власником
async def is_target_admin(bot: Bot, chat_id: int, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id, user_id)
        return member.status in ["administrator", "creator"]
    except Exception as e:
        return False

# Перевірка на наявність bot's username у команді
def check_bot_command(message: types.Message) -> bool:
    return f"@{BOT_NAME}" in message.text

# Обробка команд з помилками
async def handle_command_error(message: types.Message, e: Exception):
    await message.answer(f"Помилка: {str(e)}")

# Генерація клавіатури для розділів
def generate_help_keyboard():
    keyboard = [
        [InlineKeyboardButton(text=category, callback_data=f"help_{category}")]
        for category in commands_dict.keys()
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Функція для створення таблиці попереджень для конкретного чату
def create_warnings_table(chat_id):
    sanitized_chat_id = str(chat_id).replace("-", "_")
    table_name = f"chat_{sanitized_chat_id}_warns"

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            user_id INTEGER PRIMARY KEY,
            warns INTEGER DEFAULT 0
        )
        """)
    return table_name

# Функція для оновлення кількості повідомлень у базі даних
def update_message_count(chat_id, user_id):
    sanitized_chat_id = str(chat_id).replace("-", "_")
    table_name = f"chat_{sanitized_chat_id}_messages"

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Створення таблиці, якщо її ще немає
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            user_id INTEGER PRIMARY KEY,
            messages_count INTEGER DEFAULT 0
        )
        """)

        # Перевіряємо, чи є користувач у таблиці
        cursor.execute(f"SELECT messages_count FROM {table_name} WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()

        if result is None:
            # Якщо користувача немає, додаємо його в таблицю
            cursor.execute(f"INSERT INTO {table_name} (user_id, messages_count) VALUES (?, ?)", (user_id, 1))
        else:
            # Якщо користувач є, збільшуємо лічильник
            messages_count = result[0] + 1
            cursor.execute(f"UPDATE {table_name} SET messages_count = ? WHERE user_id = ?", (messages_count, user_id))


def field_markup(field):
    buttons = []
    buttons_row = []
    for k, v in field.items():
        buttons_row.append(types.InlineKeyboardButton(text=v, callback_data=f'walk:{k}'))
        if len(buttons_row) == 3:
            buttons.append(buttons_row)
            buttons_row = []
    return types.InlineKeyboardMarkup(inline_keyboard=buttons)

def result_text(field):
    text = ''
    string = ''
    count = 0
    for i in field.values():
        string += i
        count += 1
        if count == 3:
            text += string + '\n'
            string = ''
            count = 0
    return text


# Функція для перевірки наявності стовпця в таблиці
def column_exists(cursor, table, column):
    cursor.execute(f"PRAGMA table_info({table})")
    columns = [info[1] for info in cursor.fetchall()]
    return column in columns


async def update_timer(chat_id: int, message_id: int, end_time: datetime):
    """Оновлює таймер до заданого часу."""
    try:
        while True:
            now = datetime.now()
            remaining = end_time - now
            if remaining.total_seconds() <= 0:
                # Час завершився — оновлюємо повідомлення та завершуємо
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text="🎉 З Новим роком! 🎉"
                )
                break
            
            # Форматуємо залишок часу
            time_left = str(remaining).split(".")[0]  # Без мікросекунд
            
            # Оновлюємо повідомлення
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=f"⏳ Залишилось до Нового року: {time_left}"
                )
            except Exception as e:
                print(f"Помилка оновлення повідомлення: {e}")
            
            # Робимо паузу для зменшення навантаження
            await asyncio.sleep(5)  # Оновлюємо кожні 5 секунд
    except asyncio.CancelledError:
        # Якщо таймер скасовано, просто виходимо
        print(f"Таймер для чату {chat_id} скасовано.")
    except Exception as e:
        print(f"Помилка в таймері для чату {chat_id}: {e}")


def create_marriages_table():
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS marriages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            level INTEGER DEFAULT 1,
            start_date TEXT
        )
        """)
create_marriages_table()


def create_local_relationships_table(chat_id):
    sanitized_chat_id = str(chat_id).replace("-", "_")  # Замінити дефіси на підкреслення
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS local_relationships_{sanitized_chat_id} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            level INTEGER DEFAULT 1,
            start_date TEXT
        )
        """)


# Функція для отримання відносин
async def get_relationships(user_id, chat_id):
    # Отримання даних про відносини з БД
    sanitized_chat_id = str(chat_id).replace("-", "_")
    relationships_text = ""

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Глобальні відносини
        cursor.execute("""
        SELECT user1_id, user2_id, level, start_date FROM marriages 
        WHERE user1_id = ? OR user2_id = ?
        """, (user_id, user_id))
        global_marriages = cursor.fetchall()

        # Локальні відносини
        cursor.execute(f"""
        SELECT user1_id, user2_id, level, start_date FROM local_relationships_{sanitized_chat_id} 
        WHERE (user1_id = ? OR user2_id = ?)
        """, (user_id, user_id))
        local_marriages = cursor.fetchall()

    if global_marriages or local_marriages:
        relationships_text += f"{' ' * 15}<b>Ваші відносини:</b>{' ' * 15}\n"

        # Глобальні відносини
        if global_marriages:
            relationships_text += "\n<strong>Глобальні:</strong>\n"
            for marriage in global_marriages:
                partner_id = marriage[1] if marriage[0] == user_id else marriage[0]
                level = marriage[2]
                start_date = datetime.strptime(marriage[3], "%Y-%m-%d")
                duration = (datetime.now() - start_date).days

                relation_type = "Шлюб" if level == 2 else "Відносини"

                cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (partner_id,))
                partner_name = cursor.fetchone()
                partner_name = partner_name[0] if partner_name else "Невідомо"

                relationships_text += (
                    f"{relation_type} з <a href='tg://openmessage?user_id={partner_id}'>{partner_name}</a>  "
                    f"⌛️: {duration} днів."
                )

        # Локальні відносини
        if local_marriages:
            relationships_text += "\n<strong>Локальні:</strong>\n"
            for marriage in local_marriages:
                partner_id = marriage[1] if marriage[0] == user_id else marriage[0]
                level = marriage[2]
                start_date = datetime.strptime(marriage[3], "%Y-%m-%d")
                duration = (datetime.now() - start_date).days

                relation_type = "Шлюб" if level == 2 else "Відносини"

                cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (partner_id,))
                partner_name = cursor.fetchone()
                partner_name = partner_name[0] if partner_name else "Невідомо"

                relationships_text += (
                    f"{relation_type} з <a href='tg://openmessage?user_id={partner_id}'>{partner_name}</a>  "
                    f"⌛️: {duration} днів.\n"
                )

    return relationships_text

async def get_top_marriages(chat_id, user_id):  # Додано user_id як аргумент
    sanitized_chat_id = str(chat_id).replace("-", "_")
    marriages_text = ""

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Отримуємо всі шлюби рівня 1 і 2 для чату, сортуємо по даті створення
        cursor.execute(f"""
        SELECT user1_id, user2_id, level, start_date FROM local_relationships_{sanitized_chat_id}
        WHERE level IN (1, 2)  -- Шлюби рівня 1 та 2
        ORDER BY start_date ASC
        """)
        marriages = cursor.fetchall()

    if marriages:
        marriages_text += f"{' ' * 15}<b>Топ шлюби чату:</b>{' ' * 15}\n"

        for marriage in marriages:
            # Визначаємо партнерів
            partner_id = marriage[1] if marriage[0] == user_id else marriage[0]
            start_date = datetime.strptime(marriage[3], "%Y-%m-%d")
            duration = (datetime.now() - start_date).days

            level = marriage[2]
            relation_type = "Шлюб" if level == 2 else "Відносини"

            cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (partner_id,))
            partner_name = cursor.fetchone()
            partner_name = partner_name[0] if partner_name else "Невідомо"

            cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (marriage[0],))
            user_name = cursor.fetchone()
            user_name = user_name[0] if user_name else "Невідомо"

            marriages_text += (
                f"{relation_type} між <a href='tg://openmessage?user_id={marriage[0]}'>{user_name}</a> і "
                f"<a href='tg://openmessage?user_id={partner_id}'>{partner_name}</a>  "
                f"⌛️: {duration} днів.\n"
            )

    else:
        marriages_text = "Немає шлюбів для цього чату."

    return marriages_text




@router.message(Command("christmas"))
async def start_timer(message: Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    """Обробляє команду /christmas і запускає новий таймер."""
    chat_id = message.chat.id
    
    # Зупиняємо попередній таймер для цього чату, якщо він існує
    if chat_id in active_timers:
        task = active_timers[chat_id]["task"]
        if not task.done():  # Перевіряємо, чи не завершено
            task.cancel()  # Скасовуємо
    
    # Розраховуємо час до Нового року
    now = datetime.now()
    next_year = now.year + 1
    new_year_time = datetime(next_year, 1, 1, 0, 0, 0)
    
    # Відправляємо стартове повідомлення
    sent_message = await message.answer("⏳ Створюємо таймер...")
    
    # Створюємо нове завдання для таймера
    task = asyncio.create_task(update_timer(chat_id, sent_message.message_id, new_year_time))
    
    # Зберігаємо завдання в трекері
    active_timers[chat_id] = {
        "task": task,
        "message_id": sent_message.message_id
    }

    print(f"Запущено новий таймер для чату {chat_id}.")


@router.message(Command("create_tree"))
async def create_tree(message: Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    user_id = message.from_user.id

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Перевірка наявності колонок 'reputation' та 'presents'
        cursor.execute("PRAGMA table_info(profiles);")
        columns = [column[1] for column in cursor.fetchall()]

        # Додаємо колонку 'reputation', якщо її немає
        if "reputation" not in columns:
            cursor.execute("""
            ALTER TABLE profiles ADD COLUMN reputation INTEGER DEFAULT 0
            """)

        # Додаємо колонку 'presents', якщо її немає
        if "presents" not in columns:
            cursor.execute("""
            ALTER TABLE profiles ADD COLUMN presents INTEGER DEFAULT 0
            """)

        # Перевірка, чи є вже дерева
        cursor.execute("""
        SELECT reputation, presents FROM profiles WHERE user_id = ?
        """, (user_id,))
        result = cursor.fetchone()

        # Якщо дерево вже створене (перевірка на NULL)
        if result and result[0] is not None and result[1] is not None:
            await message.answer("Ваше дерево вже створено! Більше цією командою користуватись не треба. 🎄")
            return

        # Якщо дерева ще не створене (значення NULL)
        if result is None or result[0] is None or result[1] is None:
            # Створення або оновлення запису користувача з присвоєнням значення 1 для reputation та presents
            cursor.execute("""
            INSERT OR IGNORE INTO profiles (user_id, first_name, last_name, reputation, presents)
            VALUES (?, ?, ?, 1, 1)
            """, (user_id, message.from_user.first_name, message.from_user.last_name))

            cursor.execute("""
            UPDATE profiles
            SET bio = COALESCE(bio, ''), profile_photo_id = COALESCE(profile_photo_id, ''),
                reputation = COALESCE(reputation, 1), presents = COALESCE(presents, 1)
            WHERE user_id = ?
            """, (user_id,))

            conn.commit()

            await message.answer("Ваше дерево створено! 🎄")


@router.message(Command('xo'))
async def xo(message: Message) -> None:
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    await message.answer(
        f'{X} чи {O}',
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text=X, callback_data='select:x'),
            types.InlineKeyboardButton(text=O, callback_data='select:o')
        ]])
    )
    

@router.callback_query(lambda call: call.data.startswith('select:'))
async def game_starts(callback: CallbackQuery):
    game_id = str(callback.message.message_id) + '|' + str(callback.message.chat.id)
    xo = XO(game_id, x_symbol=X, o_symbol=O)

    if callback.data == 'select:x':
        xo.x_user_id_is(callback.from_user.id)
        return await bot.edit_message_text(
            text=f'{xo.symbols["x"]} {callback.from_user.first_name} ходить',
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=field_markup(xo.field())
        )

    if callback.data == 'select:o':
        xo.o_user_id_is(callback.from_user.id)
        return await bot.edit_message_text(
            text=f'{xo.symbols["o"]} {callback.from_user.first_name} очікує суперника',
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
                types.InlineKeyboardButton(text='X', callback_data='join')
            ]])
        )


@router.callback_query(lambda call: call.data.startswith('join'))
async def join_to_game(callback: CallbackQuery):
    game_id = str(callback.message.message_id) + '|' + str(callback.message.chat.id)
    xo = XO(game_id, x_symbol=X, o_symbol=O)
    xo.x_user_id_is(callback.from_user.id)
    o_user = await bot.get_chat(int(xo.o_user_id))
    message_text = (
        f'{xo.symbols["x"]} {callback.from_user.first_name}\n'
        f'🆚️\n{xo.symbols["o"]} {o_user.first_name}\n\n'
        f'{xo.symbols["x"]} {callback.from_user.first_name} ходить'
    )
    await bot.edit_message_text(
        message_text,
        chat_id=callback.message.chat.id, 
        message_id=callback.message.message_id, 
        reply_markup=field_markup(xo.field())
    )


@router.callback_query(lambda call: call.data.startswith('walk:'))
async def walk(callback: CallbackQuery):
    game_id = str(callback.message.message_id) + '|' + str(callback.message.chat.id)
    xo = XO(game_id, x_symbol=X, o_symbol=O)

    if xo.o_user_id == "None" and xo.who_walk() == 'o':
        xo.o_user_id_is(callback.from_user.id)

    if str(callback.from_user.id) not in [str(xo.o_user_id), str(xo.x_user_id)]:
        return await bot.answer_callback_query(callback.id, "Ти не є учасником цієї гри")
    
    if xo.who_walk() == 'x' and xo.x_user_id == callback.from_user.id:
        xo.make_move(callback.data.split(':')[1])
        
    elif xo.who_walk() == 'o' and xo.o_user_id == callback.from_user.id:
        xo.make_move(callback.data.split(':')[1]) 

    else:
        return await bot.answer_callback_query(callback.id, "Це не твій хід")
    
    if xo.does_win():
        win = ['x', 'o']
        win.remove(xo.who_walk())
        result = result_text(xo.field())
        result = result.replace('x', xo.symbols['x']).replace('o', xo.symbols['o']).replace('ㅤ', '⬜')
        win_user = await bot.get_chat(callback.from_user.id)
        lost_user = await bot.get_chat(int(xo.users[xo.who_walk()]))
        text = (
            f'{xo.symbols[win[0]]}{win_user.first_name} 🏆\n'
            f'{xo.symbols[xo.who_walk()]}{lost_user.first_name}\n\n'
            f'{result}'
        )
        xo.del_game()
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="tg channel", callback_data=f"tgc", url="https://t.me/+7WedrNk_8i9iMDAy")
        ]])
        
        return await bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=markup)
    
    if xo.draw():
        result = result_text(xo.field())
        result = result.replace('x', xo.symbols['x']).replace('o', xo.symbols['o'])
        x_user = await bot.get_chat(xo.x_user_id)
        o_user = await bot.get_chat(xo.o_user_id)
        text = (
            f'{xo.symbols["x"]}{x_user.first_name}\n'
            '🤝\n'
            f'{xo.symbols["o"]}{o_user.first_name}'
            '\n\n'
            f'{result}'
        )
        xo.del_game()
        markup = types.InlineKeyboardMarkup(inline_keyboard=[[types.InlineKeyboardButton(text="tg channel", callback_data=f"tgc", url="https://t.me/+7WedrNk_8i9iMDAy")]])
        return await bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=markup)

    if xo.o_user_id == "None" and xo.who_walk() == 'o':
        x_user = await bot.get_chat(xo.x_user_id)
        text = (
            f'{xo.symbols["x"]} {x_user.first_name} очікує на суперника\n\n'
            f'{xo.symbols["o"]} ходить'
        )
    else:
        x_user = await bot.get_chat(xo.x_user_id)
        o_user = await bot.get_chat(xo.o_user_id)
        walk_user = await bot.get_chat(xo.users[xo.who_walk()])
        text = (
            f'{xo.symbols["x"]} {x_user.first_name}\n'
            f'🆚️\n{xo.symbols["o"]} {o_user.first_name}\n\n'
            f'{xo.symbols[xo.who_walk()]} {walk_user.first_name} ходить'
        )
    await bot.edit_message_text(text, chat_id=callback.message.chat.id, message_id=callback.message.message_id, reply_markup=field_markup(xo.field()))


@router.message(Command('whois'))
async def whois_user(message: Message):
    try:
        # Перевіряємо аргументи
        args = message.text.split()
        if len(args) < 2:
            await message.reply("❌ Використання: /whois @username")
            return

        username = args[1]
        if not username.startswith("@"):
            await message.reply("❌ Юзернейм має починатися з '@', наприклад: @username")
            return

        # Пошук користувача
        try:
            chat = await bot.get_chat(username)
            await message.reply(
                f"👤 Користувач: {chat.full_name or 'N/A'}\n"
                f"🆔 ID: `{chat.id}`\n"
                f"✍️ Юзернейм: @{chat.username if chat.username else 'N/A'}",
                parse_mode="Markdown"
            )
        except Exception as inner_e:
            if "chat not found" in str(inner_e):
                await message.reply("❌ Користувача не знайдено. Можливо, він не існує або бот не має доступу.")
            else:
                await message.reply(f"⚠️ Помилка: {str(inner_e)}")

    except Exception as e:
        await message.reply(f"⚠️ Невідома помилка: {str(e)}")


@router.message(Command("profile"))
async def profile_command(message: types.Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота

    # Перевірка наявності аргументу після команди (наприклад, @username)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:  # Якщо є аргумент після команди (username)
        username = args[1].lstrip('@')  # Видаляємо символ "@" з username
        user_id = None
        try:
            # Спробуємо отримати користувача через username
            user = await bot.get_chat(username)
            user_id = user.id  # Отримуємо user_id
        except Exception as e:
            return await message.answer(f"Не вдалося знайти користувача за username {username}. Помилка: {e}")

    else:
        # Якщо аргумент після команди не передано, використовуємо reply_to_message або автора повідомлення
        user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        user_id = user.id

    # Створення таблиці для чату, якщо її не існує
    chat_id = message.chat.id
    warnings_table = create_warnings_table(chat_id)

    # Перевірка, чи є користувач у таблиці профілів
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO profiles (user_id, first_name, last_name)
        VALUES (?, ?, ?)
        """, (user_id, user.first_name, user.last_name))

        cursor.execute("SELECT first_name, last_name, bio, profile_photo_id FROM profiles WHERE user_id = ?",
                       (user_id,))
        result = cursor.fetchone()

    if not result:
        return await message.answer("Профіль не знайдено.")

    first_name, last_name, bio, profile_photo_id = result
    user_name = f"{first_name} {last_name}" if last_name else first_name
    bio_text = bio if bio else "Біографія не вказана."

    # Перевірка на наявність стовпців reputation і presents
    reputation = None
    presents = None
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Отримуємо список колонок таблиці
        cursor.execute("PRAGMA table_info(profiles);")
        columns = [column[1] for column in cursor.fetchall()]

        if "reputation" in columns:
            cursor.execute("SELECT reputation FROM profiles WHERE user_id = ?", (user_id,))
            reputation_data = cursor.fetchone()
            reputation = reputation_data[0] if reputation_data else None

        if "presents" in columns:
            cursor.execute("SELECT presents FROM profiles WHERE user_id = ?", (user_id,))
            presents_data = cursor.fetchone()
            presents = presents_data[0] if presents_data else None

    # Отримання кількості попереджень
    cursor.execute(f"SELECT warns FROM {warnings_table} WHERE user_id = ?", (user_id,))
    warns = cursor.fetchone()
    warns_count = warns[0] if warns else 0

    # Формуємо текст профілю
    profile_text = (
        f"👤 Користувач: <a href='tg://user?id={user_id}'>{user_name}</a>\n"
        f"Репутація:  ⚠️{warns_count}/3  |"
    )

    # Якщо є репутація, додаємо її
    if reputation is not None:
        profile_text += f"  ➕: {reputation}  |"

    # Якщо є подарунки, додаємо їх
    if presents is not None:
        profile_text += f"  🎁: {presents}\n"
    
    profile_text += f"Біо:\n{bio_text}\n"

    # Додаємо інформацію про відносини
    sanitized_chat_id = str(chat_id).replace("-", "_")
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Глобальні відносини
        cursor.execute("""
        SELECT user1_id, user2_id, level, start_date FROM marriages 
        WHERE user1_id = ? OR user2_id = ?
        """, (user_id, user_id))
        global_marriages = cursor.fetchall()

        # Локальні відносини
        cursor.execute(f"""
        SELECT user1_id, user2_id, level, start_date FROM local_relationships_{sanitized_chat_id} 
        WHERE (user1_id = ? OR user2_id = ?)
        """, (user_id, user_id))
        local_marriages = cursor.fetchall()

    if global_marriages or local_marriages:
        profile_text += f"{' ' * 15}<b>Ваші відносини:</b>{' ' * 15}\n"

        # Глобальні відносини
        if global_marriages:
            profile_text += "\n<strong>Глобальні:</strong>\n"
            for marriage in global_marriages:
                partner_id = marriage[1] if marriage[0] == user_id else marriage[0]
                level = marriage[2]
                start_date = datetime.strptime(marriage[3], "%Y-%m-%d")
                duration = (datetime.now() - start_date).days

                relation_type = "Шлюб" if level == 2 else "Відносини"

                cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (partner_id,))
                partner_name = cursor.fetchone()
                partner_name = partner_name[0] if partner_name else "Невідомо"

                profile_text += (
                    f"{relation_type} з <a href='tg://openmessage?user_id={partner_id}'>{partner_name}</a>  "
                    f"⌛️: {duration} днів."
                )

        # Локальні відносини
        if local_marriages:
            profile_text += "\n<strong>Локальні:</strong>\n"
            for marriage in local_marriages:
                partner_id = marriage[1] if marriage[0] == user_id else marriage[0]
                level = marriage[2]
                start_date = datetime.strptime(marriage[3], "%Y-%m-%d")
                duration = (datetime.now() - start_date).days

                relation_type = "Шлюб" if level == 2 else "Відносини"

                cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (partner_id,))
                partner_name = cursor.fetchone()
                partner_name = partner_name[0] if partner_name else "Невідомо"

                profile_text += (
                    f"{relation_type} з <a href='tg://openmessage?user_id={partner_id}'>{partner_name}</a>  "
                    f"⌛️: {duration} днів.\n"
                )

    # Відправлення профілю
    if profile_photo_id:
        try:
            await message.answer_photo(photo=profile_photo_id, caption=profile_text, parse_mode="HTML")
        except Exception:
            await message.answer("Фото профілю недоступне. Відправляю тільки текст.")
            await message.answer(profile_text, parse_mode="HTML")
    else:
        await message.answer(profile_text, parse_mode="HTML")


@router.message(Command("beat_with_belt"))
async def beat_with_belt(message: Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    voice = FSInputFile("resourses/audio/AAAA.mp3")
    await message.answer_voice(voice=voice)


@router.message(Command("stats"))
async def get_stats(message: Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    chat_id = message.chat.id
    sanitized_chat_id = str(chat_id).replace("-", "_")
    table_name = f"chat_{sanitized_chat_id}_messages"

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Отримуємо дані з таблиці з кількістю повідомлень
        cursor.execute(f"SELECT user_id, messages_count FROM {table_name} ORDER BY messages_count DESC")
        rows = cursor.fetchall()

        # Рахуємо загальну кількість повідомлень у чаті
        cursor.execute(f"SELECT SUM(messages_count) FROM {table_name}")
        total_messages = cursor.fetchone()[0] or 0

        # Формуємо повідомлення зі статистикою
        if rows:
            stats = f"Загальна кількість повідомлень у чаті: {total_messages}\n\n"
            for row in rows:
                user_id = row[0]
                messages_count = row[1]

                # Отримуємо ім'я та прізвище користувача з таблиці профілів
                cursor.execute("SELECT first_name, last_name FROM profiles WHERE user_id = ?", (user_id,))
                profile = cursor.fetchone()

                if profile:
                    first_name = profile[0]
                    last_name = profile[1] if profile[1] else ""
                    user_name = f"{first_name} {last_name}" if last_name else first_name
                else:
                    # Якщо профіль не знайдено в базі даних, отримуємо ім'я через API
                    try:
                        user = await message.bot.get_chat_member(chat_id, user_id)  # Отримуємо інформацію про користувача
                        first_name = user.user.first_name
                        last_name = user.user.last_name if user.user.last_name else ""
                        user_name = f"{first_name} {last_name}" if last_name else first_name
                    except Exception as e:
                        user_name = f"User {user_id}"  # Якщо виникла помилка або користувач не знайдений через API

                # Формуємо рядок з посиланням на повідомлення
                stats += f"<a href='tg://openmessage?user_id={user_id}'>{user_name}</a>: {messages_count} повідомлень\n"

            # Відправляємо статистику
            await message.reply(stats, parse_mode="HTML")
        else:
            await message.reply("Ще немає статистики.")


# Команда /warn
@router.message(Command("warn"))
async def warn_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    if not message.reply_to_message:
        return await message.answer("Команду /warn потрібно використовувати у відповідь на повідомлення користувача.")

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer("Тільки адміністратори можуть давати попередження.")

    target_user = message.reply_to_message.from_user
    chat_id = message.chat.id

    # Створення таблиці для чату, якщо її не існує
    warnings_table = create_warnings_table(chat_id)

    # Додавання або оновлення запису про попередження
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
        INSERT OR IGNORE INTO {warnings_table} (user_id, warns)
        VALUES (?, 0)
        """, (target_user.id,))
        cursor.execute(f"""
        UPDATE {warnings_table} SET warns = warns + 1 WHERE user_id = ?
        """, (target_user.id,))

        cursor.execute(f"SELECT warns FROM {warnings_table} WHERE user_id = ?", (target_user.id,))
        warns = cursor.fetchone()[0]

    if warns >= 3:
        await bot.ban_chat_member(chat_id, target_user.id)
        cursor.execute(f"DELETE FROM {warnings_table} WHERE user_id = ?", (target_user.id,))
        conn.commit()
        await message.answer(f"Користувач {target_user.first_name} забанений за 3 попередження.")
    else:
        await message.answer(f"Користувач {target_user.first_name} отримав {warns}/3 попереджень.")


# Інші функції з попереднього коду (наприклад, /help, /ban, /unban) залишаються без змін
# Обробник змін членства
@router.message(F.content_type.in_({"new_chat_members"}))
async def new_chat_members(message: types.Message):
    for user in message.new_chat_members:
        await message.answer(
            f"Вітаємо, {user.first_name} {user.last_name if user.last_name else ''}! 🎉\n"
            f"Дякуємо, що приєдналися до нашої групи. "
            f"Я - ваш асистент і готовий допомогти у вирішенні будь-яких питань. "
            f"Доступні команди - /help."
        )

@router.message(F.content_type.in_({"left_chat_member"}))
async def left_chat_members(message: types.Message):
    await message.answer(
        f"До побачення, {message.left_chat_member.first_name}"
        f" {message.left_chat_member.last_name if message.left_chat_member.last_name else ''}! 😔\n"
        f"Шкода, що ви покидаєте нашу групу. Надіємося побачити вас знову!"
    )

# Команда /help
@router.message(Command("help", "start"))
async def help_command(message: types.Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    keyboard = generate_help_keyboard()
    await message.answer("Оберіть розділ, щоб переглянути доступні команди:", reply_markup=keyboard)


# Обробка натискань на кнопки
@router.callback_query(lambda call: call.data.startswith("help_"))
async def help_callback_handler(callback_query: CallbackQuery):
    category = callback_query.data.split("_", 1)[1]  # Отримуємо назву розділу
    commands = commands_dict.get(category, [])

    if not commands:
        return await callback_query.answer("Розділ не знайдено.")

    commands_text = "\n".join(commands)
    await callback_query.message.edit_text(
        f"Команди в розділі <b>{category}</b>:\n\n{commands_text}",
        parse_mode="HTML",
        reply_markup=generate_help_keyboard(),
    )


# Команда /ban
@router.message(Command("ban"))
async def ban_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    if not message.reply_to_message:
        return await message.answer("Команду /ban потрібно використовувати у відповідь на повідомлення користувача.")

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer("Тільки адміністратори можуть банити користувачів.")

    target_user = message.reply_to_message.from_user
    if await is_target_admin(bot, message.chat.id, target_user.id):
        return await message.answer("Неможливо забанити адміністратора або власника.")

    await bot.ban_chat_member(message.chat.id, target_user.id)
    banned_users.add(target_user.id)
    await message.answer(f"Користувач {target_user.first_name} забанений.")


# Команда /unban
@router.message(Command("unban"))
async def unban_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    if not message.reply_to_message:
        return await message.answer("Команду /unban потрібно використовувати у відповідь на повідомлення користувача.")

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer("Тільки адміністратори можуть розпалювати користувачів.")

    target_user = message.reply_to_message.from_user
    # Перевіряємо, чи є користувач у списку забанених
    if target_user.id not in banned_users:
        return await message.answer(f"Користувач {target_user.first_name} не перебуває в бані.")

    await bot.unban_chat_member(message.chat.id, target_user.id)
    banned_users.remove(target_user.id)
    await message.answer(f"Користувач {target_user.first_name} успішно розбанений.")


# Команда /mute
@router.message(Command("mute"))
async def mute_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    if not message.reply_to_message:
        return await message.answer("Команду /mute потрібно використовувати у відповідь на повідомлення користувача.")

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer("Тільки адміністратори можуть мутити користувачів.")

    target_user = message.reply_to_message.from_user
    if await is_target_admin(bot, message.chat.id, target_user.id):
        return await message.answer("Неможливо замутити адміністратора або власника.")

    mute_time = 60 * 60  # Замутити на 1 годину
    until_date = message.date + mute_time

    await bot.restrict_chat_member(
        chat_id=message.chat.id,
        user_id=target_user.id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date
    )
    muted_users[target_user.id] = until_date
    await message.answer(f"Користувач {target_user.first_name} замучений на {mute_time // 60} хвилин.")


# Команда /unmute
@router.message(Command("unmute"))
async def unmute_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    if not message.reply_to_message:
        return await message.answer("Команду /unmute потрібно використовувати у відповідь на повідомлення користувача.")

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer("Тільки адміністратори можуть розмутити користувачів.")

    target_user = message.reply_to_message.from_user
    # Перевіряємо, чи є користувач у списку замучених
    if target_user.id not in muted_users:
        return await message.answer(f"Користувач {target_user.first_name} не перебуває в муті.")

    await bot.restrict_chat_member(
        chat_id=message.chat.id,
        user_id=target_user.id,
        permissions=ChatPermissions(can_send_messages=True)
    )
    del muted_users[target_user.id]
    await message.answer(f"Користувач {target_user.first_name} успішно розмучений.")


# Команда /report
@router.message(Command(commands=["report"]))
async def report_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        admin_list = ""

        # Визначаємо правильну таблицю для кожного чату
        chat_id = message.chat.id
        warnings_table = create_warnings_table(chat_id)

        with sqlite3.connect("DataBases/warns.db") as conn:
            cursor = conn.cursor()

            for admin in admins:
                user_id = admin.user.id

                # Перевіряємо, чи є користувач у таблиці профілів
                cursor.execute("SELECT first_name, last_name FROM profiles WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()

                if result:
                    first_name, last_name = result
                else:
                    # Використовуємо стандартне ім'я Telegram, якщо користувача немає в базі
                    first_name = admin.user.first_name
                    last_name = admin.user.last_name

                # Формуємо ім'я для відображення
                user_name = f"{first_name} {last_name}" if last_name else first_name
                admin_list += f"<a href='tg://user?id={user_id}'>{user_name}</a>\n"

        if not admin_list:
            return await message.answer("У цьому чаті немає адміністраторів.")

        await message.answer(f"Адміністратори чату:\n{admin_list}", parse_mode="HTML")
    except Exception as e:
        await handle_command_error(message, e)


# Команда /call
@router.message(Command(commands=["call"]))
async def call_command(message: types.Message, bot: Bot):
    if message.chat.type not in ["group", "supergroup"]:
        return await message.answer("Ця команда доступна лише в групах і супергрупах.")

    try:
        # Отримуємо список адміністраторів чату
        admins = await bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in admins]

        # Формуємо список згадок адміністраторів
        mentions = []
        for admin in admins:
            if admin.user.first_name is not None and admin.user.id != 777000:  # Перевірка на "видалених" акаунтів та системний акаунт
                mentions.append(f"<a href='tg://user?id={admin.user.id}'>{admin.user.first_name}</a>")

        # Зберігаємо згадки користувачів у базі даних (або додаємо вручну)
        with sqlite3.connect("DataBases/warns.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, first_name FROM profiles")
            additional_members = cursor.fetchall()

        for member in additional_members:
            user_id, first_name = member
            if user_id not in admin_ids and first_name is not None:
                # Перевірка на "видалений" акаунт через ім'я (None) або системний ID
                member_status = await bot.get_chat_member(message.chat.id, user_id)
                if member_status.status != "left" and member_status.status != "kicked":
                    mentions.append(f"<a href='tg://user?id={user_id}'>{first_name}</a>")

        # Telegram обмежує довжину повідомлення (4096 символів) і 5 тегів на повідомлення
        for i in range(0, len(mentions), 5):
            chunk = "\n".join(mentions[i:i + 5])
            await message.answer(f"Учасники чату:\n{chunk}", parse_mode="HTML")

    except Exception as e:
        await handle_command_error(message, e)


# Команда /kick
@router.message(Command("kick"))
async def kick_command(message: types.Message, bot: Bot):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    try:
        user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.get_args().split()[
            0].strip('@')

        if not await is_admin(bot, message.chat.id, user_id):
            if await is_admin(bot, message.chat.id, message.from_user.id):
                await bot.ban_chat_member(message.chat.id, user_id, until_date=0)
                await message.answer(f"Користувач {user_id} кікнутий.")
            else:
                await message.answer("Тільки адміністратори можуть кікати користувачів.")
        else:
            await message.answer("Неможливо кікнути адміністратора.")
    except Exception as e:
        await handle_command_error(message, e)



# 1. Команда для зміни нікнейму
@router.message(Command(commands=["change_nickname"]))
async def change_nickname_command(message: types.Message, command: Command):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    args = command.args  # Отримуємо аргументи команди
    if not args:
        return await message.answer("Будь ласка, вкажіть новий нікнейм після команди.")

    new_nickname = args.strip()
    user_id = message.from_user.id

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET first_name = ? WHERE user_id = ?", (new_nickname, user_id))

    await message.answer(f"Ваш нікнейм успішно змінено на {new_nickname}.")


# 2. Команда для додавання/зміни фото профілю
@router.message(Command("set_photo"))
async def set_profile_photo_command(message: types.Message):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    text = "Будь ласка, відповідайте на повідомлення з фото, щоб встановити його як фото профілю."

    if not message.reply_to_message:
        return await message.answer(text)

    if not message.reply_to_message.photo:
        return await message.answer(text)

    user_id = message.from_user.id
    photo = message.reply_to_message.photo[-1].file_id  # Беремо найвищу якість

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET profile_photo_id = ? WHERE user_id = ?", (photo, user_id))


    await message.answer("Ваше фото профілю успішно оновлено.")


# 3. Команда для додавання/зміни біографії
@router.message(Command(commands=["set_bio"]))
async def set_bio_command(message: types.Message, command: Command):
    if message.chat.type in ["group", "supergroup"] and not check_bot_command(message):
        return  # Завершуємо функцію, якщо немає згадки бота
    bio = command.args  # Отримуємо аргументи команди
    if not bio:
        return await message.answer("Будь ласка, вкажіть текст біографії після команди.")

    user_id = message.from_user.id

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET bio = ? WHERE user_id = ?", (bio, user_id))

    await message.answer("Ваша біографія успішно оновлена.")




@router.message(lambda message: message.text.lower().startswith(("!!відносини", "!!розлучитись")))
async def handle_relationship_message(message: types.Message):
    text = message.text.lower()
    reply = message.reply_to_message
    
    if text.startswith("!!відносини"):
        if not reply:
            return await message.reply("Ця команда працює лише у відповідь на повідомлення.")

    sender_id = message.from_user.id
    receiver_id = reply.from_user.id

    if sender_id == receiver_id:
        return await message.reply("Ви не можете почати відносини із самим собою.")

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()
        if text.startswith("!!відносини"):
            cursor.execute("""
            SELECT * FROM marriages WHERE user1_id = ? OR user2_id = ?
            """, (receiver_id, receiver_id))
            if cursor.fetchone():
                return await message.reply("Цей користувач вже зайнятий у відносинах.")

        if text.startswith("!!відносини"):
            cursor.execute("""
            SELECT * FROM marriages WHERE user1_id = ? OR user2_id = ?
            """, (sender_id, sender_id))
            if cursor.fetchone():
                return await message.reply("Ви вже зайняті у відносинах.")

        cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (receiver_id,))
        receiver_name = cursor.fetchone()
        if receiver_name:
            receiver_name = receiver_name[0]
        else:
            receiver_name = reply.from_user.first_name

    # Клавіатура з кнопками "Так" і "Ні"
    yes_button = InlineKeyboardButton(text="Так", callback_data=f"relationship_confirm_{sender_id}_{receiver_id}_yes")
    no_button = InlineKeyboardButton(text="Ні", callback_data=f"relationship_confirm_{sender_id}_{receiver_id}_no")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[yes_button, no_button]])

    if text.startswith("!!відносини"):
        # Перевірка, чи відповідаєте ви саме тому користувачу
        if message.reply_to_message.from_user.id != message.from_user.id:
            await message.reply(
                f"<a href='tg://user?id={receiver_id}'>{receiver_name}</a>, чи згодні ви розпочати відносини?",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await message.reply("Ви не можете підтвердити або заперечити свою власну пропозицію!")

    if text.startswith("!!розлучитись"):
        with sqlite3.connect("DataBases/warns.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT * FROM marriages WHERE 
            (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
            """, (sender_id, receiver_id, receiver_id, sender_id))
            if not cursor.fetchone():
                return await message.reply("У вас немає відносин із цим користувачем.")

        await message.reply(
            f"<a href='tg://user?id={receiver_id}'>{receiver_name}</a>, чи згодні ви розлучитись? ці дані є глобальними та буде шкода втратити прогресію.",
            reply_markup=keyboard,
            parse_mode="HTML"
        )


@router.callback_query(lambda call: call.data.startswith("relationship_confirm_"))
async def handle_relationship_confirmation(callback_query: CallbackQuery):
    # Отримуємо дані з callback_data
    data = callback_query.data.split("_")
    sender_id = int(data[2])
    receiver_id = int(data[3])
    action = data[4]  # "yes" або "no"

    # Перевіряємо, чи це дійсно та команда для цього користувача
    if callback_query.from_user.id != receiver_id:
        return await callback_query.answer("Це не ваша пропозиція для підтвердження.", show_alert=True)

    # Логіка для підтвердження чи відмови від відносин
    if action == "yes":
        if "відносини" in callback_query.message.text.lower():
            with sqlite3.connect("DataBases/warns.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                SELECT * FROM marriages WHERE 
                (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                """, (sender_id, receiver_id, receiver_id, sender_id))
                marriage_exists = cursor.fetchone()

                if marriage_exists:
                    return await callback_query.answer("У вас вже є відносини або шлюб.", show_alert=True)

                cursor.execute("""
                INSERT INTO marriages (user1_id, user2_id, start_date) VALUES (?, ?, ?)
                """, (sender_id, receiver_id, datetime.now().strftime("%Y-%m-%d")))

            await callback_query.message.reply(
                "Вітаємо! Відносини розпочато. Ви можете використовувати команду /rolewords для покращення рівня відносин."
            )
            await callback_query.message.delete() 

        elif "розлучитись" in callback_query.message.text.lower():
            with sqlite3.connect("DataBases/warns.db") as conn:
                cursor = conn.cursor()
                cursor.execute("""
                DELETE FROM marriages WHERE 
                (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                """, (sender_id, receiver_id, receiver_id, sender_id))

            await callback_query.message.reply("Відносини успішно завершено.")
            await callback_query.message.delete() 
    else:
        await callback_query.answer("Пропозиція відхилена.")
        await callback_query.message.delete() 


@router.message(lambda message: message.text.lower().startswith(("!відносини", "!розлучитись")))
async def handle_local_relationship_message(message: types.Message):
    text = message.text.lower()
    reply = message.reply_to_message
    chat_id = message.chat.id

    if text.startswith("!відносини"):
        if not reply:
            return await message.reply("Ця команда працює лише у відповідь на повідомлення.")

    sender_id = message.from_user.id
    receiver_id = reply.from_user.id

    if sender_id == receiver_id:
        return await message.reply("Ви не можете почати або завершити відносини із самим собою.")

    sanitized_chat_id = str(chat_id).replace("-", "_")
    
    # Створення таблиці для поточного чату, якщо її не існує
    create_local_relationships_table(chat_id)

    
    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT first_name FROM profiles WHERE user_id = ?", (receiver_id,))
        receiver_name = cursor.fetchone()
        if receiver_name:
            receiver_name = receiver_name[0]
        else:
            receiver_name = reply.from_user.first_name
        

        # Якщо команда початку відносин
        if text.startswith("!відносини"):
            cursor.execute(f"""
            SELECT * FROM local_relationships_{sanitized_chat_id} WHERE (user1_id = ? OR user2_id = ?)
            """, (receiver_id, receiver_id))
            if cursor.fetchone():
                return await message.reply("Цей користувач вже зайнятий у відносинах у цьому чаті.")

            cursor.execute(f"""
            SELECT * FROM local_relationships_{sanitized_chat_id} WHERE (user1_id = ? OR user2_id = ?)
            """, (sender_id, sender_id))
            if cursor.fetchone():
                return await message.reply("Ви вже зайняті у відносинах у цьому чаті.")

            # Клавіатура з кнопками "Так" і "Ні"
            yes_button = InlineKeyboardButton(text="Так", callback_data=f"localrelationship_confirm_{sender_id}_{receiver_id}_yes")
            no_button = InlineKeyboardButton(text="Ні", callback_data=f"localrelationship_confirm_{sender_id}_{receiver_id}_no")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[no_button, yes_button]])

            await message.reply(
                f"<a href='tg://user?id={receiver_id}'>{receiver_name}</a>, чи згодні ви розпочати локальні відносини?",
                reply_markup=keyboard,
                parse_mode="HTML"
            )

        # Якщо команда завершення відносин
        elif text.startswith("!розлучитись"):
            cursor.execute(f"""
            SELECT * FROM local_relationships_{sanitized_chat_id} WHERE 
            ((user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?))
            """, (sender_id, receiver_id, receiver_id, sender_id))
            
            if not cursor.fetchone():
                return await message.reply("У вас немає відносин із цим користувачем у цьому чаті.")

            # Клавіатура з кнопками "Так" і "Ні"
            yes_button = InlineKeyboardButton(text="Так", callback_data=f"localrelationship_confirm_{sender_id}_{receiver_id}_yes")
            no_button = InlineKeyboardButton(text="Ні", callback_data=f"localrelationship_confirm_{sender_id}_{receiver_id}_no")
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[no_button, yes_button]])

            await message.reply(
                f"<a href='tg://user?id={receiver_id}'>Ви хочете розлучитись з {receiver_name}?</a>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )


@router.callback_query(lambda call: call.data.startswith("localrelationship_confirm_"))
async def handle_local_relationship_confirmation(callback_query: CallbackQuery):
    # Отримуємо дані з callback_data
    data = callback_query.data.split("_")
    sender_id = int(data[2])
    receiver_id = int(data[3])
    action = data[4]  # "yes" або "no"
    # Очищуємо chat_id від потенційно небезпечних символів
    sanitized_chat_id = str(callback_query.message.chat.id).replace("-", "_")


    # Перевіряємо, чи це дійсно та команда для цього користувача
    if callback_query.from_user.id != receiver_id:
        return await callback_query.answer("Це не ваша пропозиція для підтвердження.", show_alert=True)

    # Логіка для підтвердження чи відмови від відносин
    if action == "yes":
        if "відносини" in callback_query.message.text.lower():
            with sqlite3.connect("DataBases/warns.db") as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                SELECT * FROM local_relationships_{sanitized_chat_id} WHERE 
                (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                """, (sender_id, receiver_id, receiver_id, sender_id))
                marriage_exists = cursor.fetchone()

                if marriage_exists:
                    return await callback_query.answer("У вас вже є відносини або шлюб.", show_alert=True)

                # Вставка нових відносин
                cursor.execute(f"""
                INSERT INTO local_relationships_{sanitized_chat_id} (user1_id, user2_id, start_date) VALUES (?, ?, ?)
                """, (sender_id, receiver_id, datetime.now().strftime("%Y-%m-%d")))

            await callback_query.message.reply(
                "Вітаємо! Локальні відносини розпочато. Ви можете використовувати команду /rolewords для покращення рівня відносин."
            )
            await callback_query.message.delete() 

        elif "розлучитись" in callback_query.message.text.lower():
            with sqlite3.connect("DataBases/warns.db") as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                DELETE FROM local_relationships_{sanitized_chat_id} WHERE 
                (user1_id = ? AND user2_id = ?) OR (user1_id = ? AND user2_id = ?)
                """, (sender_id, receiver_id, receiver_id, sender_id))

            await callback_query.message.reply("Локальні відносини успішно завершено.")
            await callback_query.message.delete() 
    else:
        await callback_query.answer("Пропозиція відхилена.")
        await callback_query.message.delete() 


# Обробка команди для шлюбу/відносин
@router.message(lambda message: message.text.lower().startswith("!шлюби"))
async def marriages_command(message: types.Message):
    # Перевірка наявності аргументу після команди (наприклад, @username)
    args = message.text.split(maxsplit=1)
    if len(args) > 1:  # Якщо є аргумент після команди (username)
        username = args[1].lstrip('@')  # Видаляємо символ "@" з username
        user_id = None
        try:
            # Спробуємо отримати користувача через username
            user = await bot.get_chat(username)
            user_id = user.id  # Отримуємо user_id
        except Exception as e:
            return await message.answer(f"Не вдалося знайти користувача за username {username}. Помилка: {e}")

    else:
        # Якщо аргумент після команди не передано, використовуємо reply_to_message або автора повідомлення
        user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        user_id = user.id

    # Отримуємо відносини
    relationships_text = await get_relationships(user_id, message.chat.id)

    if relationships_text:
        await message.answer(relationships_text, parse_mode="HTML")
    else:
        await message.answer("Відносин не знайдено.", parse_mode="HTML")


# Обробка команди для топ шлюбів
@router.message(lambda message: message.text.lower().startswith("!топшлюбів"))
async def top_marriages_command(message: types.Message):
    user_id = message.from_user.id  # Беремо user_id відправника повідомлення

    # Отримуємо топ шлюби для чату
    marriages_text = await get_top_marriages(message.chat.id, user_id)

    if marriages_text:
        await message.answer(marriages_text, parse_mode="HTML")
    else:
        await message.answer("Немає локальних шлюбів в цьому чаті.", parse_mode="HTML")


# Команда для роздачі репутації
@router.message(lambda message: message.text == "+")
async def give_reputation(message: Message):
    user_id = message.from_user.id

    # Перевірка, чи є відповідь на повідомлення
    if message.reply_to_message:
        target_user_id = message.reply_to_message.from_user.id
    else:
        return

    # Перевірка на самопожертвування (не можна додавати репутацію самому собі)
    if user_id == target_user_id:
        await message.answer("Не можна додавати репутацію самому собі!")
        return

    # Отримання поточної дати
    current_date = date.today().isoformat()  # Використовуємо date, щоб уникнути конфлікту

    with sqlite3.connect("DataBases/warns.db") as conn:
        cursor = conn.cursor()

        # Перевірка і створення таблиці `profiles`, якщо її немає
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            reputation INTEGER DEFAULT 0
        )
        """)

        # Перевірка і створення таблиці `reputation_logs`, якщо її немає
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reputation_logs (
            giver_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            date_given TEXT NOT NULL,
            PRIMARY KEY (giver_id, receiver_id, date_given)
        )
        """)

        # Перевірка, чи вже давали репутацію цьому користувачу сьогодні
        cursor.execute("""
        SELECT 1
        FROM reputation_logs
        WHERE giver_id = ? AND receiver_id = ? AND date_given = ?
        """, (user_id, target_user_id, current_date))
        already_given = cursor.fetchone()

        if already_given:
            await message.answer("Ви вже дали репутацію цьому користувачу сьогодні.")
            return

        # Додаємо запис у таблицю логів
        cursor.execute("""
        INSERT INTO reputation_logs (giver_id, receiver_id, date_given)
        VALUES (?, ?, ?)
        """, (user_id, target_user_id, current_date))

        # Оновлюємо репутацію для користувача
        cursor.execute("""
        SELECT reputation
        FROM profiles
        WHERE user_id = ?
        """, (target_user_id,))
        result = cursor.fetchone()

        if result is None:
            # Якщо користувач не існує в таблиці profiles
            cursor.execute("""
            INSERT INTO profiles (user_id, reputation)
            VALUES (?, 1)
            """, (target_user_id,))
        else:
            cursor.execute("""
            UPDATE profiles
            SET reputation = reputation + 1
            WHERE user_id = ?
            """, (target_user_id,))

        conn.commit()

        # Отримання імені користувача для повідомлення
        user_name = message.reply_to_message.from_user.full_name
        await message.answer(f"Ви додали +1 до репутації користувача {user_name}. 🎉")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message):
    text = message.text
    chat_id = message.chat.id
    user_id = message.from_user.id

    # Перевіряємо чи є повідомлення відповіддю на повідомлення бота
    is_reply_to_bot = message.reply_to_message and message.reply_to_message.from_user.is_bot

    # Перевіряємо, чи містить повідомлення слово "сину" (незалежно від регістру)
    contains_son = any(word in text.lower() for word in son)

    # Зберігаємо повідомлення до файлу
    save_message_to_file(text)

    # Оновлюємо лічильник повідомлень у базі
    update_message_count(chat_id, user_id)
    
    if "слава україні" in text.lower():
        await message.reply("Героям слава!")
    elif is_reply_to_bot or contains_son:
        random_quote = get_random_message()
        await message.reply(random_quote)

    # Генеруємо випадкове число від 1 до 10
    elif random.randint(1, 100) == 5:
        random_quote = get_random_message()
        if random_quote:
            await message.reply(random_quote)
        else:
            await message.reply("Історія повідомлень поки що порожня.")
