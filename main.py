import asyncio
import logging

from aiogram import Bot, Dispatcher
from app.handlers import router
from app.database.models import async_main
from config import TG_TOKEN
from apscheduler.schedulers.asyncio import AsyncIOScheduler

bot = Bot(token=TG_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

async def main():
    await async_main()
    scheduler.start()
    dp.include_router(router)
    await dp.start_polling(bot, scheduler=scheduler)

async def send_notification(chat_id, message):
    await bot.send_message(chat_id, message)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exit")