import sqlite3
from aiogram import types, Router, Bot, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
import random

router = Router()

# Список забанених та замучених користувачів
banned_users = set()
muted_users = {}

# Ініціалізація бази даних
conn = sqlite3.connect("warns.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS warns (
    user_id INTEGER,
    chat_id INTEGER,
    first_name TEXT,
    last_name TEXT,
    warns INTEGER DEFAULT 0,
    bio TEXT DEFAULT '',
    profile_photo_id TEXT DEFAULT '',
    PRIMARY KEY (user_id, chat_id)
)
""")
conn.commit()


# Файл для збереження історії повідомлень
HISTORY_FILE = "chat_history.txt"

# Лічильники для чатів
message_counters = {}



# Збереження текстового повідомлення в файл
def save_message_to_file(text):
    with open(HISTORY_FILE, "a", encoding="utf-8") as file:
        file.write(f"{text}\n")

# Зчитування випадкового повідомлення з файлу
def get_random_quote():
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as file:
            messages = file.readlines()
        return random.choice(messages).strip() if messages else None
    except FileNotFoundError:
        return None


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


# Перевірка на наявність "@heros_son_bot" у команді
def check_bot_command(message: types.Message) -> bool:
    return "@heros_son_bot" in message.text


# Обробка команд з помилками
async def handle_command_error(message: types.Message, e: Exception):
    await message.answer(f"Помилка: {str(e)}")

# Опис категорій і команд
commands_dict = {
    "Зміна акаунту": [
        "/profile@heros_son_bot - Переглянути свій профіль",
        "/set_photo@heros_son_bot - Змінити фото профілю",
        "/set_bio@heros_son_bot - Додати/змінити біографію",
        "/change_nickname@heros_son_bot - Змінити нікнейм"
    ],
    "Адміністрування": [
        "/ban@heros_son_bot [user] - Забанити користувача",
        "/unban@heros_son_bot [user] - Розбанити користувача",
        "/mute@heros_son_bot [user] [time] - Замутити користувача",
        "/unmute@heros_son_bot [user] - Розмутити користувача",
        "/warn@heros_son_bot - Дати попередження",
        "/kick@heros_son_bot [user] - Кікнути користувача",
        "/report@heros_son_bot - Показати всіх адміністраторів"
    ],
    "Інше": [
        "/help@heros_son_bot - Показати список команд",
        "/start@heros_son_bot - Запустити бота",
        "/info@heros_son_bot - Інформація про бота"
    ]
}

# Генерація клавіатури для розділів
def generate_help_keyboard():
    keyboard = [
        [InlineKeyboardButton(text=category, callback_data=f"help_{category}")]
        for category in commands_dict.keys()
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# Команда /profile
@router.message(Command("profile"))
async def profile_command(message: types.Message):
    if check_bot_command(message):
        user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
        user_id = user.id
        chat_id = message.chat.id

        # Перевіряємо, чи існує запис для цього користувача в поточному чаті
        cursor.execute("""
        INSERT OR IGNORE INTO warns (user_id, chat_id, first_name, last_name, warns)
        VALUES (?, ?, ?, ?, 0)
        """, (user_id, chat_id, user.first_name, user.last_name))
        conn.commit()

        cursor.execute("""
        SELECT first_name, last_name, warns, bio, profile_photo_id FROM warns
        WHERE user_id = ? AND chat_id = ?
        """, (user_id, chat_id))
        result = cursor.fetchone()

        if result:
            first_name, last_name, warns, bio, profile_photo_id = result
            user_name = f"{first_name} {last_name}" if last_name else first_name
            bio_text = bio if bio else "Біографія не вказана."

            profile_text = (f"Користувач: <a href='tg://user?id={user_id}'>{user_name}</a>\n"
                            f"ID: {user_id}\n"
                            f"Чат: {chat_id}\n"
                            f"Кількість попереджень: {warns}/3\n"
                            f"Біографія: {bio_text}")

            if profile_photo_id:
                await message.answer_photo(photo=profile_photo_id, caption=profile_text, parse_mode="HTML")
            else:
                await message.answer(profile_text, parse_mode="HTML")
        else:
            await message.answer("Профіль не знайдено.")


# Команда /warn
@router.message(Command("warn"))
async def warn_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        if not message.reply_to_message:
            await message.answer("Команду /warn потрібно використовувати у відповідь на повідомлення користувача.")
            return

        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("Тільки адміністратори можуть давати попередження.")
            return

        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id

        if await is_target_admin(bot, message.chat.id, target_user_id):
            await message.answer("Неможливо дати попередження адміністратору або власнику.")
            return

        chat_id = message.chat.id
        first_name = target_user.first_name
        last_name = target_user.last_name

        # Додаємо або оновлюємо запис у базі даних
        cursor.execute("""
        INSERT OR IGNORE INTO warns (user_id, chat_id, first_name, last_name, warns)
        VALUES (?, ?, ?, ?, 0)
        """, (target_user_id, chat_id, first_name, last_name))
        cursor.execute("""
        UPDATE warns SET warns = warns + 1 WHERE user_id = ? AND chat_id = ?
        """, (target_user_id, chat_id))
        conn.commit()

        # Отримуємо оновлену кількість попереджень
        cursor.execute("""
        SELECT warns FROM warns WHERE user_id = ? AND chat_id = ?
        """, (target_user_id, chat_id))
        warns = cursor.fetchone()[0]

        if warns >= 3:
            await bot.ban_chat_member(chat_id, target_user_id)
            cursor.execute("""
            DELETE FROM warns WHERE user_id = ? AND chat_id = ?
            """, (target_user_id, chat_id))
            conn.commit()
            await message.answer(f"Користувач {first_name} забанений за 3 попередження.")
        else:
            await message.answer(f"Користувач {first_name} отримав {warns}/3 попереджень.")


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
@router.message(Command("help"))
async def help_command(message: types.Message):
    keyboard = generate_help_keyboard()
    await message.answer("Оберіть розділ, щоб переглянути доступні команди:", reply_markup=keyboard)


# Обробка натискань на кнопки
@router.callback_query(lambda call: call.data.startswith("help_"))
async def help_callback_handler(callback_query: CallbackQuery):
    category = callback_query.data.split("_", 1)[1]  # Отримуємо назву розділу
    commands = commands_dict.get(category, [])

    if commands:
        commands_text = "\n".join(commands)
        await callback_query.message.edit_text(
            f"Команди в розділі <b>{category}</b>:\n\n{commands_text}",
            parse_mode="HTML",
            reply_markup=generate_help_keyboard()
        )
    else:
        await callback_query.answer("Розділ не знайдено.")


# Команда /ban
@router.message(Command("ban"))
async def ban_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        if not message.reply_to_message:
            await message.answer("Команду /ban потрібно використовувати у відповідь на повідомлення користувача.")
            return

        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("Тільки адміністратори можуть банити користувачів.")
            return

        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id

        if await is_target_admin(bot, message.chat.id, target_user_id):
            await message.answer("Неможливо забанити адміністратора або власника.")
            return

        await bot.ban_chat_member(message.chat.id, target_user_id)
        banned_users.add(target_user_id)
        await message.answer(f"Користувач {target_user.first_name} забанений.")


# Команда /unban
@router.message(Command("unban"))
async def unban_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        if not message.reply_to_message:
            await message.answer("Команду /unban потрібно використовувати у відповідь на повідомлення користувача.")
            return

        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("Тільки адміністратори можуть розпалювати користувачів.")
            return

        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id

        # Перевіряємо, чи є користувач у списку забанених
        if target_user_id not in banned_users:
            await message.answer(f"Користувач {target_user.first_name} не перебуває в бані.")
            return

        await bot.unban_chat_member(message.chat.id, target_user_id)
        banned_users.remove(target_user_id)
        await message.answer(f"Користувач {target_user.first_name} успішно розбанений.")


# Команда /mute
@router.message(Command("mute"))
async def mute_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        if not message.reply_to_message:
            await message.answer("Команду /mute потрібно використовувати у відповідь на повідомлення користувача.")
            return

        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("Тільки адміністратори можуть мутити користувачів.")
            return

        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id

        if await is_target_admin(bot, message.chat.id, target_user_id):
            await message.answer("Неможливо замутити адміністратора або власника.")
            return

        mute_time = 60 * 60  # Замутити на 1 годину
        until_date = message.date + mute_time

        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            permissions=ChatPermissions(can_send_messages=False),
            until_date=until_date
        )
        muted_users[target_user_id] = until_date
        await message.answer(f"Користувач {target_user.first_name} замучений на {mute_time // 60} хвилин.")


# Команда /unmute
@router.message(Command("unmute"))
async def unmute_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        if not message.reply_to_message:
            await message.answer("Команду /unmute потрібно використовувати у відповідь на повідомлення користувача.")
            return

        if not await is_admin(bot, message.chat.id, message.from_user.id):
            await message.answer("Тільки адміністратори можуть розмутити користувачів.")
            return

        target_user = message.reply_to_message.from_user
        target_user_id = target_user.id

        # Перевіряємо, чи є користувач у списку замучених
        if target_user_id not in muted_users:
            await message.answer(f"Користувач {target_user.first_name} не перебуває в муті.")
            return

        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=target_user_id,
            permissions=ChatPermissions(can_send_messages=True)
        )
        del muted_users[target_user_id]
        await message.answer(f"Користувач {target_user.first_name} успішно розмучений.")


# Команда /report
@router.message(Command(commands=["report"]))
async def report_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        try:
            admins = await bot.get_chat_administrators(message.chat.id)
            admin_list = ""

            for admin in admins:
                user_id = admin.user.id

                # Перевіряємо, чи є користувач у базі
                cursor.execute("SELECT first_name, last_name FROM warns WHERE user_id = ?", (user_id,))
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

            if admin_list:
                await message.answer(f"Адміністратори чату:\n{admin_list}", parse_mode="HTML")
            else:
                await message.answer("У цьому чаті немає адміністраторів.")
        except Exception as e:
            await handle_command_error(message, e)


# Команда /kick
@router.message(Command("kick"))
async def kick_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
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

# Нові функції додаються тут

# 1. Команда для зміни нікнейму
@router.message(Command(commands=["change_nickname"]))
async def change_nickname_command(message: types.Message, command: Command):
    if check_bot_command(message):
        args = command.args  # Отримуємо аргументи команди
        if args:
            new_nickname = args.strip()
            user_id = message.from_user.id

            cursor.execute("UPDATE warns SET first_name = ? WHERE user_id = ?", (new_nickname, user_id))
            conn.commit()

            await message.answer(f"Ваш нікнейм успішно змінено на {new_nickname}.")
        else:
            await message.answer("Будь ласка, вкажіть новий нікнейм після команди.")


# 2. Команда для додавання/зміни фото профілю
@router.message(Command("set_photo"))
async def set_profile_photo_command(message: types.Message):
    if check_bot_command(message):
        if message.reply_to_message and message.reply_to_message.photo:
            user_id = message.from_user.id
            photo = message.reply_to_message.photo[-1].file_id  # Беремо найвищу якість

            cursor.execute("UPDATE warns SET profile_photo_id = ? WHERE user_id = ?", (photo, user_id))
            conn.commit()

            await message.answer("Ваше фото профілю успішно оновлено.")
        else:
            await message.answer("Будь ласка, відповідайте на повідомлення з фото, щоб встановити його як фото профілю.")


# 3. Команда для додавання/зміни біографії
@router.message(Command(commands=["set_bio"]))
async def set_bio_command(message: types.Message, command: Command):
    if check_bot_command(message):
        bio = command.args  # Отримуємо аргументи команди
        if bio:
            user_id = message.from_user.id

            cursor.execute("UPDATE warns SET bio = ? WHERE user_id = ?", (bio, user_id))
            conn.commit()

            await message.answer("Ваша біографія успішно оновлена.")
        else:
            await message.answer("Будь ласка, вкажіть текст біографії після команди.")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_text_message(message: Message):
    chat_id = message.chat.id
    text = message.text

    await message.reply('text')

    # Зберігаємо повідомлення до файлу
    save_message_to_file(text)

    # Оновлюємо лічильник для чату
    if chat_id not in message_counters:
        message_counters[chat_id] = 0
    message_counters[chat_id] += 1

    # Раз на 1-10 повідомлень відправляємо рандомну цитату
    if message_counters[chat_id] >= random.randint(1, 10):
        random_quote = get_random_quote()
        if random_quote:
            await message.reply(random_quote)
        else:
            await message.reply("Історія повідомлень поки що порожня.")
        message_counters[chat_id] = 0  # Скидаємо лічильник
