import logging
from aiogram import Bot, Dispatcher
from app.config import TOKEN
from app.handlers import router

bot = Bot(token=TOKEN)
dp = Dispatcher()


if __name__ == "__main__":
    dp.include_router(router)
    dp.run_polling(bot)