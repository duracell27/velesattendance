import asyncio
import logging
from aiogram import Bot, Dispatcher
from storage import JsonStorage
from aiogram.types import BotCommand
from config import BOT_TOKEN
from handlers import registration, attendance, admin, schedule_edit, admin_report

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=JsonStorage("fsm_storage.json"))

    dp.include_router(registration.router)
    dp.include_router(attendance.router)
    dp.include_router(admin_report.router)
    dp.include_router(schedule_edit.router)
    dp.include_router(admin.router)

    await bot.set_my_commands([BotCommand(command="start", description="Головне меню")])

    logging.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
