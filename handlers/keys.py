from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from datetime import datetime

from config import DOMAIN, SUB_PATH
from database import get_or_create_user, get_active_subscription
from xui_api import get_total_traffic

router = Router()


def format_bytes(b: int) -> str:
    if b < 1024:
        return f"{b} B"
    elif b < 1024**2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024**3:
        return f"{b / 1024**2:.1f} MB"
    else:
        return f"{b / 1024**3:.2f} GB"


def get_sub_link(vpn_uuid: str) -> str:
    return f"https://{DOMAIN}{SUB_PATH}/{vpn_uuid}"


@router.callback_query(F.data == "mykey")
async def mykey_handler(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)
    sub = get_active_subscription(user["id"])

    if not sub:
        buttons = [
            [InlineKeyboardButton(text="🤍 Купить подписку", callback_data="buy")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback.message.edit_text(
            "❌ У тебя нет активной подписки.\nКупи подписку чтобы получить ключ!",
            reply_markup=kb,
        )
        return

    expires = datetime.fromisoformat(sub["expires_at"])
    days_left = (expires - datetime.utcnow()).days
    sub_link = get_sub_link(user["vpn_uuid"])

    text = (
        f"🔑 <b>Твой ключ Syntax VPN</b>\n\n"
        f"📅 Подписка до: {expires.strftime('%d.%m.%Y')}\n"
        f"⏰ Осталось: {days_left} дн.\n\n"
        f"🔗 <b>Ссылка подписки:</b>\n"
        f"<code>{sub_link}</code>\n\n"
        f"📱 Скопируй и вставь в:\n"
        f"• <b>Android</b>: V2RayNG, Hiddify\n"
        f"• <b>iOS</b>: Streisand, V2Box\n"
        f"• <b>Windows</b>: Hiddify, Nekoray\n"
        f"• <b>macOS</b>: Hiddify, V2Box\n\n"
        f"Все серверы загрузятся автоматически."
    )

    buttons = [
        [InlineKeyboardButton(text="📊 Мой трафик", callback_data="traffic")],
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="guide")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "traffic")
async def traffic_handler(callback: CallbackQuery):
    await callback.answer("📊 Загружаю статистику...")
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)
    sub = get_active_subscription(user["id"])

    if not sub:
        await callback.message.answer("❌ У тебя нет активной подписки.")
        return

    email = f"tg_{callback.from_user.id}"
    traffic = await get_total_traffic(email)

    text = (
        f"📊 <b>Твой трафик</b>\n\n"
        f"⬆️ Отправлено: {format_bytes(traffic['up'])}\n"
        f"⬇️ Получено: {format_bytes(traffic['down'])}\n"
        f"📦 Всего: {format_bytes(traffic['total'])}\n"
    )

    buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="mykey")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)