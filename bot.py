import asyncio
import logging

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import TELEGRAM_BOT_TOKEN
from database import init_db
from handlers import all_routers

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

temp_router = Router()


@temp_router.message(F.photo)
async def get_photo_id(message: types.Message):
    photo = message.photo[-1]
    await message.answer(f"file_id:\n<code>{photo.file_id}</code>")


async def main():
    init_db()
    for r in all_routers:
        dp.include_router(r)
    dp.include_router(temp_router)
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())