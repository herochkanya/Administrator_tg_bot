import logging
from aiogram import Bot, Dispatcher
from config import TOKEN
from handlers import router

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    dp.include_router(router)
    dp.run_polling(bot)
