from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import ADMIN_TELEGRAM_IDS
from database import get_all_users_count, get_active_subs_count, get_db

router = Router()


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


def get_total_revenue() -> int:
    with get_db() as db:
        row = db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE status = 'confirmed'"
        ).fetchone()
        return int(row["total"])


def get_recent_payments(limit: int = 10) -> list[dict]:
    with get_db() as db:
        rows = db.execute("""
            SELECT p.amount, p.plan_id, p.created_at, u.username, u.telegram_id
            FROM payments p
            JOIN users u ON p.user_id = u.id
            WHERE p.status = 'confirmed'
            ORDER BY p.id DESC
            LIMIT ?
        """, (limit,)).fetchall()
        return [dict(r) for r in rows]


@router.callback_query(F.data == "admin")
async def admin_handler(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_TELEGRAM_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await callback.answer()

    users_count = get_all_users_count()
    active_subs = get_active_subs_count()
    total_revenue = get_total_revenue()
    recent_payments = get_recent_payments()

    payments_text = ""
    for p in recent_payments:
        username = f"@{p['username']}" if p['username'] else str(p['telegram_id'])
        date = p['created_at'][:10] if p['created_at'] else "—"
        payments_text += f"  {username} — {int(p['amount'])}₽ ({p['plan_id']}) {date}\n"

    if not payments_text:
        payments_text = "  Пока нет оплат\n"

    text = (
        f"⚙️ <b>Админ-панель</b>\n\n"
        f"👥 Всего пользователей: {users_count}\n"
        f"✅ Активных подписок: {active_subs}\n"
        f"💰 Заработано: {total_revenue}₽\n\n"
        f"📋 <b>Последние оплаты:</b>\n"
        f"{payments_text}"
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
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)