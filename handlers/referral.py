from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from database import get_referral_count, get_referral_bonus_days

router = Router()

REFERRAL_VIDEO = "BAACAgIAAxkBAAICKmm1WlbRxNOjJ4GFnefGbfKOhmqMAALYnQACs0qpSSpDhog24PY9OgQ"

BOT_USERNAME = "syntxvpn_bot"


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


@router.callback_query(F.data == "referral")
async def referral_handler(callback: CallbackQuery):
    await callback.answer()

    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    friends_count = get_referral_count(callback.from_user.id)
    bonus_days = get_referral_bonus_days(callback.from_user.id)

    text = (
        "🎁 <b>Приглашайте друзей и получайте бонусы!</b>\n\n"
        "За каждого друга, который присоединится по вашей ссылке, "
        "вы получаете <b>+3 дня бесплатного доступа</b>. "
        "Чем больше друзей — тем дольше пользуетесь бесплатно 😉\n\n"
        "Поделитесь ссылкой и начните получать бонусы уже сегодня!\n\n"
        f"👥 Приглашено друзей: {friends_count}\n"
        f"🎁 Получено бонусных дней: {bonus_days}\n\n"
        f"🔗 Ваша реферальная ссылка:\n"
        f"<code>{ref_link}</code>"
    )

    buttons = [
        [InlineKeyboardButton(
            text="📨 Пригласить друзей",
            url=f"https://t.me/share/url?url={ref_link}"
        )],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if has_media(callback.message):
        await callback.message.delete()
    else:
        try:
            await callback.message.delete()
        except Exception:
            pass

    await callback.message.answer_video(video=REFERRAL_VIDEO, caption=text, reply_markup=kb)