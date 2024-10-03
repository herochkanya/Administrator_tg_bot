import sqlite3
from aiogram import types, Router, Bot, F
from aiogram.filters import Command
from aiogram.types import ChatPermissions

router = Router()

# Список забанених та замучених користувачів
banned_users = set()
muted_users = {}

# Ініціалізація бази даних
conn = sqlite3.connect("warns.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS warns (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    warns INTEGER
)
""")
conn.commit()


# Функція перевірки, чи є користувач адміністратором
async def is_admin(bot: Bot, chat_id, user_id):
    member = await bot.get_chat_member(chat_id, user_id)
    return member.status in ["administrator", "creator"]


# Перевірка на наявність "@heros_son_bot" у команді
def check_bot_command(message: types.Message) -> bool:
    return "@heros_son_bot" in message.text


# Обробка команд з помилками
async def handle_command_error(message: types.Message, e: Exception):
    await message.answer(f"Помилка: {str(e)}")


# Команда /profile
@router.message(Command("profile"))
async def profile_command(message: types.Message):
    if check_bot_command(message):
        if message.reply_to_message:
            user = message.reply_to_message.from_user
        else:
            user = message.from_user

        user_id = user.id
        first_name = user.first_name
        last_name = user.last_name
        cursor.execute("SELECT warns FROM warns WHERE user_id = ?", (user_id,))
        result = cursor.fetchone()
        warns = result[0] if result else 0

        user_name = f"{first_name} {last_name}" if last_name else first_name
        profile_text = (f"Користувач: <a href='tg://user?id={user_id}'>{user_name}</a>\n"
                        f"ID: {user_id}\n"
                        f"Кількість попереджень: {warns}/3")
        await message.answer(profile_text, parse_mode="HTML")


# Команда /warn
@router.message(Command("warn"))
async def warn_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        if message.reply_to_message:
            if not await is_admin(bot, message.chat.id, message.from_user.id):
                await message.answer("Тільки адміністратори можуть давати попередження.")
                return

            user = message.reply_to_message.from_user
            user_id = user.id
            first_name = user.first_name
            last_name = user.last_name

            cursor.execute("INSERT OR IGNORE INTO warns (user_id, first_name, last_name, warns) VALUES (?, ?, ?, ?)",
                           (user_id, first_name, last_name, 0))
            cursor.execute("UPDATE warns SET warns = warns + 1 WHERE user_id = ?", (user_id,))
            conn.commit()

            cursor.execute("SELECT warns FROM warns WHERE user_id = ?", (user_id,))
            warns = cursor.fetchone()[0]

            if warns >= 3:
                if await is_admin(bot, message.chat.id, user_id):
                    await bot.restrict_chat_member(message.chat.id, user_id,
                                                   permissions=ChatPermissions(can_send_messages=True))
                    await bot.promote_chat_member(message.chat.id, user_id,
                                                  can_change_info=False,
                                                  can_delete_messages=False,
                                                  can_invite_users=True,
                                                  can_restrict_members=False,
                                                  can_pin_messages=False,
                                                  can_promote_members=False)
                    cursor.execute("DELETE FROM warns WHERE user_id = ?", (user_id,))
                    conn.commit()
                    await message.answer(f"Користувач {first_name} забанений за 3 попередження.")
                else:
                    await bot.ban_chat_member(message.chat.id, user_id)
                    cursor.execute("DELETE FROM warns WHERE user_id = ?", (user_id,))
                    conn.commit()
                    await message.answer(f"Користувач {first_name} забанений за 3 попередження.")
            else:
                await message.answer(f"Користувач {first_name} отримав {warns}/3 попереджень.")
        else:
            await message.answer("Команду /warn потрібно використовувати у відповідь на повідомлення користувача.")


# Обробник змін членства
@router.message(F.content_type.in_({"new_chat_members", "left_chat_member"}))
async def membership_changes(message: types.Message):
    if message.new_chat_members:
        for user in message.new_chat_members:
            await message.answer(f"Вітаємо, {user.first_name} {user.last_name if user.last_name else ''}! 🎉\n"
                                 f"Дякуємо, що приєдналися до нашої групи. "
                                 f"Я - ваш асистент і готовий допомогти у вирішенні будь-яких питань. "
                                 f"Доступні команди - /help.")
    elif message.left_chat_member:
        await message.answer(f"До побачення, {message.left_chat_member.first_name}"
                             f" {message.left_chat_member.last_name if message.left_chat_member.last_name else ''}! 😔\n"
                             f"Шкода, що ви покидаєте нашу групу. Надіємося побачити вас знову!")


# Команда /help
@router.message(Command("help"))
async def help_command(message: types.Message):
    if check_bot_command(message):
        help_text = (
            "/help@heros_son_bot - Показати всі команди\n"
            "/ban@heros_son_bot [user] - Забанити користувача\n"
            "/unban@heros_son_bot [user] - Розбанити користувача\n"
            "/mute@heros_son_bot [user] [time] - Замутити користувача на певний час (в годинах)\n"
            "/unmute@heros_son_bot [user] - Розмутити користувача\n"
            "/report@heros_son_bot - Показати всіх адміністраторів\n"
            "/kick@heros_son_bot [user] - Кікнути користувача\n"
            "/profile@heros_son_bot - Показати профіль користувача\n"
            "/warn@heros_son_bot - Дати попередження користувачу"
        )
        await message.answer(help_text)


# Команда /ban
@router.message(Command("ban"))
async def ban_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        try:
            user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.get_args().split()[
                0]

            if not await is_admin(bot, message.chat.id, user_id):
                if await is_admin(bot, message.chat.id, message.from_user.id):
                    await bot.ban_chat_member(message.chat.id, user_id)
                    banned_users.add(user_id)
                    await message.answer(f"Користувач {user_id} забанений.")
                else:
                    await message.answer("Тільки адміністратори можуть банити користувачів.")
            else:
                await message.answer("Неможливо забанити адміністратора.")
        except Exception as e:
            await handle_command_error(message, e)


# Команда /unban
@router.message(Command("unban"))
async def unban_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        try:
            user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.get_args().split()[
                0]

            if user_id in banned_users:
                await bot.unban_chat_member(message.chat.id, user_id)
                banned_users.remove(user_id)
                await message.answer(f"Користувач {user_id} розбанений.")
            else:
                await message.answer(f"Користувач {user_id} не в бані.")
        except Exception as e:
            await handle_command_error(message, e)


# Команда /mute
@router.message(Command("mute"))
async def mute_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        try:
            args = message.get_args().split()
            user_id = message.reply_to_message.from_user.id if message.reply_to_message else args[0]
            mute_time = int(args[1]) * 60 if len(args) > 1 else 60  # Default to 1 hour if no time specified
            until_date = message.date + mute_time

            if not await is_admin(bot, message.chat.id, user_id):
                if await is_admin(bot, message.chat.id, message.from_user.id):
                    await bot.restrict_chat_member(message.chat.id, user_id, permissions=ChatPermissions(

                    ), until_date=until_date)
                    muted_users[user_id] = until_date
                    await message.answer(f"Користувач {user_id} замучений на {mute_time // 60} хвилин.")
                else:
                    await message.answer("Тільки адміністратори можуть мутити користувачів.")
            else:
                await message.answer("Неможливо замутити адміністратора.")
        except Exception as e:
            await handle_command_error(message, e)


# Команда /unmute
@router.message(Command("unmute"))
async def unmute_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        try:
            user_id = message.reply_to_message.from_user.id if message.reply_to_message else message.get_args().split()[
                0]

            if user_id in muted_users:
                await bot.restrict_chat_member(message.chat.id, user_id, permissions=ChatPermissions(
                    can_send_messages=True))
                del muted_users[user_id]
                await message.answer(f"Користувач {user_id} розмучений.")
            else:
                await message.answer(f"Користувач {user_id} не в муті.")
        except Exception as e:
            await handle_command_error(message, e)


# Команда /report
@router.message(Command("report"))
async def report_command(message: types.Message, bot: Bot):
    if check_bot_command(message):
        try:
            admins = await bot.get_chat_administrators(message.chat.id)
            admin_list = ""
            for admin in admins:
                admin_name = f"{admin.user.first_name} {admin.user.last_name}" if admin.user.last_name else\
                    admin.user.first_name
                admin_list += f"<a href='tg://user?id={admin.user.id}'>{admin_name}</a>\n"
            await message.answer(f"Адміністратори чату:\n{admin_list}", parse_mode="HTML")
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
