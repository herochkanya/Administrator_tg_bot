import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from handlers import router
from aiogram.methods import DeleteWebhook

# Ініціалізація бота та диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

async def main():
    # Видаляємо вебхук, якщо він встановлений
    await bot(DeleteWebhook(drop_pending_updates=True))

    # Додаємо маршрутизатор
    dp.include_router(router)

    # Запускаємо довготривале опитування
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
