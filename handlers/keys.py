from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from datetime import datetime
import math

from config import DOMAIN, SUB_PATH
from database import get_or_create_user, get_active_subscription
from xui_api import get_total_traffic

router = Router()

MYKEY_VIDEO = "BAACAgIAAxkBAAID2Wm2pLS46GHCGgnilxqURJhVvMNZAALlpwACpBq4SeajMUdtylrPOgQ"


def format_gb(b: int) -> str:
    return f"{b / 1024**3:.1f}"


def get_sub_link(vpn_uuid: str) -> str:
    return f"https://{DOMAIN}{SUB_PATH}/{vpn_uuid}"


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


def days_word(n: int) -> str:
    if 11 <= n % 100 <= 19:
        return "дней"
    last = n % 10
    if last == 1:
        return "день"
    if 2 <= last <= 4:
        return "дня"
    return "дней"


@router.callback_query(F.data == "mykey")
async def mykey_handler(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)
    sub = get_active_subscription(user["id"])

    if not sub:
        text = "❌ У тебя нет активной подписки.\nКупи подписку чтобы получить ключ!"
        buttons = [
            [InlineKeyboardButton(text="🤍 Купить подписку", callback_data="buy")],
            [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer_video(video=MYKEY_VIDEO, caption=text, reply_markup=kb)
        return

    email = f"tg_{callback.from_user.id}"
    traffic = await get_total_traffic(email)
    used_gb = format_gb(traffic["total"])
    sub_link = get_sub_link(user["vpn_uuid"])
    expires = datetime.fromisoformat(sub["expires_at"])
    days_left = math.ceil((expires - datetime.utcnow()).total_seconds() / 86400)

    text = (
        f"👁‍🗨 Лимит трафика: ♾️Безлимит\n"
        f"🌐 В этом месяце: {used_gb}гб\n"
        f"📱 Лимит устройств: 3шт\n"
        f"⏳ Осталось {days_left} {days_word(days_left)}\n"
        f"🕯 ID: {callback.from_user.id}\n\n"
        f"🗝 Ключ:\n"
        f"<code>{sub_link}</code>\n\n"
        f"⁉️ Есть вопросы с подключением?\n"
        f"Обратись в поддержку на главной,\n"
        f"👌 мы обязательно поможем"
    )
    happ_redirect = f"https://{DOMAIN}/r?url={sub_link}"
    buttons = [
        [InlineKeyboardButton(text="📥 Добавить VPN в приложение", url=happ_redirect)],
        [InlineKeyboardButton(text="📲 Установить приложение", callback_data="download_app")],
        [InlineKeyboardButton(text="🛒 Продлить действие VPN-ключа", callback_data="buy")],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")]
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_video(video=MYKEY_VIDEO, caption=text, reply_markup=kb)