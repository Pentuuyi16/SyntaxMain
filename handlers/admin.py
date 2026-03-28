from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import ADMIN_TELEGRAM_IDS
from database import get_all_users_count, get_active_subs_count, get_db

router = Router()


class BroadcastState(StatesGroup):
    waiting_for_message = State()


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


def get_all_user_ids() -> list[int]:
    with get_db() as db:
        rows = db.execute("SELECT telegram_id FROM users").fetchall()
        return [r["telegram_id"] for r in rows]


# Хранилище последней рассылки — chat_id: message_id
_last_broadcast: dict[int, int] = {}


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
        [InlineKeyboardButton(text="🗑 Удалить последнюю рассылку", callback_data="admin_broadcast_delete")],
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


@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_TELEGRAM_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await callback.answer()

    await state.set_state(BroadcastState.waiting_for_message)

    buttons = [[InlineKeyboardButton(text="🚪 Отмена", callback_data="admin_broadcast_cancel")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.answer(
        "📢 <b>Рассылка</b>\n\n"
        "Отправь сообщение которое хочешь разослать всем пользователям.\n"
        "Поддерживается текст, фото, видео.",
        reply_markup=kb
    )


@router.callback_query(F.data == "admin_broadcast_cancel")
async def admin_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer("Отменено")
    await callback.message.delete()


@router.message(BroadcastState.waiting_for_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_TELEGRAM_IDS:
        return

    await state.clear()

    user_ids = get_all_user_ids()
    total = len(user_ids)
    success = 0
    failed = 0

    status_msg = await message.answer(f"⏳ Рассылка началась... 0/{total}")

    from bot import bot
    for i, user_id in enumerate(user_ids):
        try:
            if message.photo:
                sent = await bot.send_photo(
                    user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.caption or "",
                )
            elif message.video:
                sent = await bot.send_video(
                    user_id,
                    video=message.video.file_id,
                    caption=message.caption or "",
                )
            elif message.animation:
                sent = await bot.send_animation(
                    user_id,
                    animation=message.animation.file_id,
                    caption=message.caption or "",
                )
            else:
                sent = await bot.send_message(
                    user_id,
                    text=message.html_text,
                )
            _last_broadcast[user_id] = sent.message_id
            success += 1
        except Exception:
            failed += 1

        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(f"⏳ Рассылка... {i+1}/{total}")
            except Exception:
                pass

    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"👥 Всего: {total}\n"
        f"✅ Успешно: {success}\n"
        f"❌ Ошибок: {failed}"
    )


@router.callback_query(F.data == "admin_broadcast_delete")
async def admin_broadcast_delete(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_TELEGRAM_IDS:
        await callback.answer("⛔️ Нет доступа", show_alert=True)
        return
    await callback.answer()

    if not _last_broadcast:
        await callback.message.answer("❌ Нет сохранённой рассылки для удаления.")
        return

    total = len(_last_broadcast)
    success = 0
    failed = 0

    status_msg = await callback.message.answer(f"⏳ Удаление... 0/{total}")

    from bot import bot
    for i, (user_id, msg_id) in enumerate(_last_broadcast.items()):
        try:
            await bot.delete_message(user_id, msg_id)
            success += 1
        except Exception:
            failed += 1

        if (i + 1) % 10 == 0:
            try:
                await status_msg.edit_text(f"⏳ Удаление... {i+1}/{total}")
            except Exception:
                pass

    _last_broadcast.clear()

    await status_msg.edit_text(
        f"✅ Удаление завершено!\n\n"
        f"✅ Удалено: {success}\n"
        f"❌ Ошибок: {failed}"
    )