import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.models import async_main
from confi import TG_TOKEN

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()


async def main():
    await async_main()
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")