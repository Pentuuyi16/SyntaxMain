"""
Telegram-бот SyntaxVPN — точка входа
"""

import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from config import TELEGRAM_BOT_TOKEN
from database import init_db, get_all_active_subscriptions, deactivate_subscription

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


async def check_expired_subscriptions():
    """Фоновая задача — проверяет истёкшие подписки и отправляет уведомления"""
    while True:
        try:
            subs = get_all_active_subscriptions()
            now = datetime.utcnow()

            for sub in subs:
                expires = datetime.fromisoformat(sub["expires_at"])

                if expires < now:
                    # Подписка истекла
                    deactivate_subscription(sub["id"])

                    if sub["plan_id"] == "trial" or sub["plan_id"] == "referral":
                        text = (
                            "<b>Пробный период закончился, но это не повод прощаться 😉</b>\n\n"
                            "Продлите подписку и продолжайте пользоваться "
                            "всеми преимуществами без ограничений!"
                        )
                    else:
                        text = (
                            "<b>Подписка закончилась, но это не повод прощаться 😉</b>\n\n"
                            "Продлите её и продолжайте пользоваться "
                            "всеми преимуществами без ограничений!"
                        )

                    buttons = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🤍 Купить подписку", callback_data="buy")],
                    ])

                    try:
                        await bot.send_message(
                            sub["telegram_id"],
                            text,
                            reply_markup=buttons,
                        )
                        logger.info(f"Expired notification sent to {sub['telegram_id']}")
                    except Exception as e:
                        logger.error(f"Failed to send expired notification to {sub['telegram_id']}: {e}")

        except Exception as e:
            logger.error(f"check_expired_subscriptions error: {e}")

        await asyncio.sleep(300)  # Проверяем каждые 5 минут


async def main():
    init_db()
    from handlers import all_routers
    for r in all_routers:
        dp.include_router(r)
    dp.include_router(temp_router)

    # Запускаем фоновую задачу
    asyncio.create_task(check_expired_subscriptions())

    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())