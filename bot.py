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
from database import (
    init_db,
    get_all_active_subscriptions,
    get_expired_active_subscriptions,
    deactivate_subscription,
    has_notification,
    add_notification,
    clear_notifications,
)

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
    """Фоновая задача — проверяет истёкшие подписки и напоминания"""
    await asyncio.sleep(10)
    logger.info("check_expired_subscriptions task started")

    while True:
        try:
            # 1. Напоминание за 1 день
            subs = get_all_active_subscriptions()
            now = datetime.utcnow()

            for sub in subs:
                expires = datetime.fromisoformat(sub["expires_at"])
                hours_left = (expires - now).total_seconds() / 3600

                if 0 < hours_left <= 24:
                    notif_key = f"remind_1day_{sub['id']}"
                    if not has_notification(sub["telegram_id"], notif_key):
                        if sub["plan_id"] in ("trial", "referral"):
                            text = (
                                "<b>⏳ До окончания пробной подписки — всего 1 день…</b>\n\n"
                                "Продлите её сейчас, чтобы сохранить доступ без ограничений ✨"
                            )
                        else:
                            text = (
                                "<b>⏳ До окончания подписки — всего 1 день…</b>\n\n"
                                "Продлите её сейчас, чтобы сохранить доступ без ограничений ✨"
                            )

                        buttons = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="🤍 Купить подписку", callback_data="buy")],
                            [InlineKeyboardButton(text="🚪 Главное меню", callback_data="back_start")],
                        ])

                        try:
                            await bot.send_message(sub["telegram_id"], text, reply_markup=buttons)
                            add_notification(sub["telegram_id"], notif_key)
                            logger.info(f"1-day reminder sent to {sub['telegram_id']}")
                        except Exception as e:
                            logger.error(f"Failed to send 1-day reminder to {sub['telegram_id']}: {e}")

            # 2. Подписка истекла
            expired_subs = get_expired_active_subscriptions()

            if expired_subs:
                logger.info(f"Found {len(expired_subs)} expired subscriptions")

            for sub in expired_subs:
                deactivate_subscription(sub["id"])
                clear_notifications(sub["telegram_id"])

                if sub["plan_id"] in ("trial", "referral"):
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
                    await bot.send_message(sub["telegram_id"], text, reply_markup=buttons)
                    logger.info(f"Expired notification sent to {sub['telegram_id']}")
                except Exception as e:
                    logger.error(f"Failed to send expired notification to {sub['telegram_id']}: {e}")

        except Exception as e:
            logger.error(f"check_expired_subscriptions error: {e}")

        await asyncio.sleep(300)


async def main():
    init_db()
    from handlers import all_routers
    for r in all_routers:
        dp.include_router(r)
    dp.include_router(temp_router)

    asyncio.create_task(check_expired_subscriptions())

    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())