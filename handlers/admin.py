from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import ADMIN_TELEGRAM_IDS
from database import get_all_users_count, get_active_subs_count

router = Router()


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


@router.callback_query(F.data == "admin")
async def admin_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_TELEGRAM_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await callback.answer()

    users_count = get_all_users_count()
    active_subs = get_active_subs_count()

    text = (
        f"⚙️ <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"✅ Активных подписок: {active_subs}\n"
    )

    buttons = [
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    if has_media(callback.message):
        await callback.message.delete()
        await callback.message.answer(text, reply_markup=kb)
    else:
        await callback.message.edit_text(text, reply_markup=kb)