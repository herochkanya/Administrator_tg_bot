import sqlite3
from aiogram import types, Router, Bot, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message, FSInputFile
import random
import config


router = Router()

# Список забанених та замучених користувачів
banned_users = set()
muted_users = {}

son = [
    "сину", "сина", "синочок", "хіро",
    "hero", "son", "myson", "child", "kiddo", "junior"
]

# Ініціалізація бази даних
with sqlite3.connect("warns.db") as conn:
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
        "🔵 /change_nickname - Змінити нікнейм"
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
    "Інше": [
        "❓ /help - Показати список команд",
        "🔵 /start - Запустити бота",
        "📜 /stats - Переглянути статистику повідомлень"
    ]
}


# Створення або відкриття бази даних
def create_connection():
    return sqlite3.connect('history.db')

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
    # Видалення символів нового рядка (\n) та об'єднання всіх рядків тексту в один рядок
    single_line_text = " ".join(text.split())
    try:
        with create_connection() as conn:
            cursor = conn.cursor()
            # Перевірка наявності дубліката
            cursor.execute('SELECT COUNT(*) FROM messages WHERE text = ?', (single_line_text,))
            count = cursor.fetchone()[0]
            if count == 0:
                # Вставка нового повідомлення, якщо дубліката немає
                cursor.execute('''
                    INSERT OR IGNORE INTO messages (text)
                    VALUES (?)
                ''', (single_line_text,))
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
    return f"@{config.BOT_NAME}" in message.text

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

    with sqlite3.connect("warns.db") as conn:
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

    with sqlite3.connect("warns.db") as conn:
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




# Команда /profile
@router.message(Command("profile"))
async def profile_command(message: types.Message):
    user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    chat_id = message.chat.id

    # Створення таблиці для чату, якщо її не існує
    warnings_table = create_warnings_table(chat_id)

    # Перевірка, чи є користувач у таблиці профілів
    with sqlite3.connect("warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO profiles (user_id, first_name, last_name)
        VALUES (?, ?, ?)
        """, (user.id, user.first_name, user.last_name))

        cursor.execute("SELECT first_name, last_name, bio, profile_photo_id FROM profiles WHERE user_id = ?",
                       (user.id,))
        result = cursor.fetchone()

    if not result:
        return await message.answer("Профіль не знайдено.")

    first_name, last_name, bio, profile_photo_id = result
    user_name = f"{first_name} {last_name}" if last_name else first_name
    bio_text = bio if bio else "Біографія не вказана."

    # Отримання кількості попереджень
    cursor.execute(f"SELECT warns FROM {warnings_table} WHERE user_id = ?", (user.id,))
    warns = cursor.fetchone()
    warns_count = warns[0] if warns else 0

    profile_text = (
        f"Користувач: <a href='tg://user?id={user.id}'>{user_name}</a>\n"
        f"ID: {user.id}\n"
        f"Кількість попереджень: {warns_count}/3\n"
        f"Біографія: {bio_text}"
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
    voice = FSInputFile("resourses/audio/AAAA.mp3")
    await message.answer_voice(voice=voice)


@router.message(Command("stats"))
async def get_stats(message: Message):
    chat_id = message.chat.id
    sanitized_chat_id = str(chat_id).replace("-", "_")
    table_name = f"chat_{sanitized_chat_id}_messages"

    with sqlite3.connect("warns.db") as conn:
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
    if not message.reply_to_message:
        return await message.answer("Команду /warn потрібно використовувати у відповідь на повідомлення користувача.")

    if not await is_admin(bot, message.chat.id, message.from_user.id):
        return await message.answer("Тільки адміністратори можуть давати попередження.")

    target_user = message.reply_to_message.from_user
    chat_id = message.chat.id

    # Створення таблиці для чату, якщо її не існує
    warnings_table = create_warnings_table(chat_id)

    # Додавання або оновлення запису про попередження
    with sqlite3.connect("warns.db") as conn:
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
    try:
        admins = await bot.get_chat_administrators(message.chat.id)
        admin_list = ""

        # Визначаємо правильну таблицю для кожного чату
        chat_id = message.chat.id
        warnings_table = create_warnings_table(chat_id)

        with sqlite3.connect("warns.db") as conn:
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


# Команда /kick
@router.message(Command("kick"))
async def kick_command(message: types.Message, bot: Bot):
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
    args = command.args  # Отримуємо аргументи команди
    if not args:
        return await message.answer("Будь ласка, вкажіть новий нікнейм після команди.")

    new_nickname = args.strip()
    user_id = message.from_user.id

    with sqlite3.connect("warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET first_name = ? WHERE user_id = ?", (new_nickname, user_id))

    await message.answer(f"Ваш нікнейм успішно змінено на {new_nickname}.")


# 2. Команда для додавання/зміни фото профілю
@router.message(Command("set_photo"))
async def set_profile_photo_command(message: types.Message):
    text = "Будь ласка, відповідайте на повідомлення з фото, щоб встановити його як фото профілю."

    if not message.reply_to_message:
        return await message.answer(text)

    if not message.reply_to_message.photo:
        return await message.answer(text)

    user_id = message.from_user.id
    photo = message.reply_to_message.photo[-1].file_id  # Беремо найвищу якість

    with sqlite3.connect("warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET profile_photo_id = ? WHERE user_id = ?", (photo, user_id))


    await message.answer("Ваше фото профілю успішно оновлено.")


# 3. Команда для додавання/зміни біографії
@router.message(Command(commands=["set_bio"]))
async def set_bio_command(message: types.Message, command: Command):
    bio = command.args  # Отримуємо аргументи команди
    if not bio:
        return await message.answer("Будь ласка, вкажіть текст біографії після команди.")

    user_id = message.from_user.id

    with sqlite3.connect("warns.db") as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE profiles SET bio = ? WHERE user_id = ?", (bio, user_id))

    await message.answer("Ваша біографія успішно оновлена.")


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

    if is_reply_to_bot or contains_son:
        random_quote = get_random_message()
        await message.reply(random_quote)

    # Генеруємо випадкове число від 1 до 10
    elif random.randint(1, 100) == 5:
        random_quote = get_random_message()
        if random_quote:
            await message.reply(random_quote)
        else:
            await message.reply("Історія повідомлень поки що порожня.")
