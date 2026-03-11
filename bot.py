"""
Telegram-бот SyntaxVPN — точка входа
"""

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
    await message.answer(f"photo file_id:\n<code>{photo.file_id}</code>")


@temp_router.message(F.video)
async def get_video_id(message: types.Message):
    await message.answer(f"video file_id:\n<code>{message.video.file_id}</code>")


@temp_router.message(F.animation)
async def get_animation_id(message: types.Message):
    await message.answer(f"animation file_id:\n<code>{message.animation.file_id}</code>")


@temp_router.message(F.video_note)
async def get_video_note_id(message: types.Message):
    await message.answer(f"video_note file_id:\n<code>{message.video_note.file_id}</code>")


async def main():
    init_db()
    for r in all_routers:
        dp.include_router(r)
    dp.include_router(temp_router)
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())