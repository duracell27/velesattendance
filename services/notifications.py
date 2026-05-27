from aiogram import Bot
from config import HR_ADMIN_IDS


async def notify_hr_checkin(bot: Bot, name: str, time_str: str, photo_file_id: str) -> None:
    caption = f"📍 {name} прийшла на роботу о {time_str}"
    for admin_id in HR_ADMIN_IDS:
        await bot.send_photo(admin_id, photo=photo_file_id, caption=caption)


async def notify_hr_checkout(
    bot: Bot, name: str, time_str: str, hours_str: str, photo_file_id: str
) -> None:
    caption = f"🚪 {name} пішла з роботи о {time_str} (відпрацювала {hours_str})"
    for admin_id in HR_ADMIN_IDS:
        await bot.send_photo(admin_id, photo=photo_file_id, caption=caption)
