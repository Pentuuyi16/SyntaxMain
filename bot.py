"""
Telegram-бот SyntaxVPN
aiogram 3 + ЮKassa + 3X-UI API
"""

import asyncio
import logging
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
)
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_TELEGRAM_IDS,
    PLANS,
    TRIAL_ENABLED,
    TRIAL_DURATION_DAYS,
    TRIAL_TRAFFIC_GB,
    DOMAIN,
    SUB_PATH,
)
from database import (
    init_db,
    get_or_create_user,
    get_active_subscription,
    create_subscription,
    has_used_trial,
    mark_trial_used,
    create_payment as db_create_payment,
    confirm_payment as db_confirm_payment,
    get_payment_by_yukassa_id,
    get_all_users_count,
    get_active_subs_count,
    deactivate_subscription,
)
from xui_api import add_client_to_all_servers, remove_client_from_all_servers, get_total_traffic
from payments import create_payment as yk_create_payment, check_payment as yk_check_payment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()


def format_bytes(b: int) -> str:
    """Форматирует байты в человекочитаемый вид"""
    if b < 1024:
        return f"{b} B"
    elif b < 1024**2:
        return f"{b / 1024:.1f} KB"
    elif b < 1024**3:
        return f"{b / 1024**2:.1f} MB"
    else:
        return f"{b / 1024**3:.2f} GB"


def get_sub_link(vpn_uuid: str) -> str:
    """Генерирует ссылку подписки для пользователя"""
    return f"https://{DOMAIN}{SUB_PATH}/{vpn_uuid}"


# ==================
# /start
# ==================

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)
    sub = get_active_subscription(user["id"])

    text = (
        f"👋 <b>Добро пожаловать в SyntaxVPN!</b>\n\n"
        f"🔒 Безопасный VPN с серверами в разных локациях.\n"
        f"Один ключ — доступ ко всем серверам.\n\n"
    )

    if sub:
        expires = datetime.fromisoformat(sub["expires_at"])
        days_left = (expires - datetime.utcnow()).days
        text += (
            f"✅ У тебя активная подписка\n"
            f"📅 Осталось: <b>{days_left} дн.</b>\n\n"
        )

    buttons = [
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton(text="🔑 Мой ключ", callback_data="mykey")],
        [InlineKeyboardButton(text="📊 Мой трафик", callback_data="traffic")],
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="guide")],
    ]

    if TRIAL_ENABLED and not has_used_trial(message.from_user.id) and not sub:
        buttons.insert(0, [
            InlineKeyboardButton(text="🎁 Пробный период (бесплатно)", callback_data="trial")
        ])

    if message.from_user.id in ADMIN_TELEGRAM_IDS:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(text, reply_markup=kb)


# ==================
# Пробный период
# ==================

@router.callback_query(F.data == "trial")
async def trial_handler(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)

    if has_used_trial(callback.from_user.id):
        await callback.message.answer("❌ Ты уже использовал пробный период.")
        return

    if get_active_subscription(user["id"]):
        await callback.message.answer("✅ У тебя уже есть активная подписка!")
        return

    # Создаём подписку
    email = f"tg_{callback.from_user.id}"
    traffic_bytes = TRIAL_TRAFFIC_GB * 1024 * 1024 * 1024
    expiry_ms = int((datetime.utcnow() + timedelta(days=TRIAL_DURATION_DAYS)).timestamp() * 1000)

    # Добавляем на все серверы
    ok = await add_client_to_all_servers(
        vpn_uuid=user["vpn_uuid"],
        email=email,
        traffic_limit_bytes=traffic_bytes,
        expiry_time=expiry_ms,
    )

    if not ok:
        await callback.message.answer("❌ Ошибка при создании ключа. Попробуй позже.")
        return

    create_subscription(user["id"], "trial", TRIAL_DURATION_DAYS, TRIAL_TRAFFIC_GB)
    mark_trial_used(callback.from_user.id)

    sub_link = get_sub_link(user["vpn_uuid"])
    text = (
        f"🎉 <b>Пробный период активирован!</b>\n\n"
        f"⏰ Срок: {TRIAL_DURATION_DAYS} дн.\n"
        f"📦 Трафик: {TRIAL_TRAFFIC_GB} ГБ\n\n"
        f"🔗 <b>Твоя ссылка подписки:</b>\n"
        f"<code>{sub_link}</code>\n\n"
        f"Скопируй и вставь в приложение (V2RayNG, Hiddify, Streisand).\n"
        f"Все серверы появятся автоматически! 🚀"
    )
    await callback.message.answer(text)


# ==================
# Покупка
# ==================

@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    await callback.answer()

    buttons = []
    for plan_id, plan in PLANS.items():
        btn_text = f"{plan['name']} — {plan['price']}₽"
        buttons.append([InlineKeyboardButton(text=btn_text, callback_data=f"pay_{plan_id}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")])
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        "🛒 <b>Выбери тариф:</b>\n\n"
        "Все тарифы включают:\n"
        "• Доступ ко всем серверам\n"
        "• Безлимитный трафик\n"
        "• До 3 устройств одновременно\n"
    )
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("pay_"))
async def pay_handler(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.replace("pay_", "")

    if plan_id not in PLANS:
        await callback.message.answer("❌ Тариф не найден.")
        return

    plan = PLANS[plan_id]
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)

    # Создаём платёж в ЮKassa
    payment = yk_create_payment(
        amount=plan["price"],
        plan_id=plan_id,
        telegram_id=callback.from_user.id,
        description=f"SyntaxVPN — {plan['name']}",
    )

    if not payment:
        await callback.message.answer("❌ Ошибка при создании платежа. Попробуй позже.")
        return

    # Сохраняем в БД
    db_create_payment(user["id"], plan_id, plan["price"], payment["payment_id"])

    buttons = [
        [InlineKeyboardButton(text="💳 Оплатить", url=payment["confirmation_url"])],
        [InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data=f"check_{payment['payment_id']}"
        )],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        f"💰 <b>Оплата: {plan['name']}</b>\n\n"
        f"Сумма: <b>{plan['price']}₽</b>\n\n"
        f"Нажми «Оплатить», затем «Я оплатил»."
    )
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data.startswith("check_"))
async def check_payment_handler(callback: CallbackQuery):
    payment_id = callback.data.replace("check_", "")

    # Проверяем в ЮKassa
    result = yk_check_payment(payment_id)

    if result["status"] == "succeeded" and result["paid"]:
        await callback.answer("✅ Оплата подтверждена!")

        # Получаем данные
        db_payment = get_payment_by_yukassa_id(payment_id)
        if not db_payment:
            await callback.message.answer("❌ Ошибка: платёж не найден в базе.")
            return

        if db_payment["status"] == "confirmed":
            await callback.message.answer("✅ Этот платёж уже обработан!")
            return

        plan_id = db_payment["plan_id"]
        plan = PLANS[plan_id]
        user = get_or_create_user(callback.from_user.id, callback.from_user.username)
        email = f"tg_{callback.from_user.id}"

        # Время истечения
        expiry_ms = int(
            (datetime.utcnow() + timedelta(days=plan["duration_days"])).timestamp() * 1000
        )
        traffic_bytes = plan["traffic_gb"] * 1024 * 1024 * 1024 if plan["traffic_gb"] > 0 else 0

        # Добавляем на все серверы
        ok = await add_client_to_all_servers(
            vpn_uuid=user["vpn_uuid"],
            email=email,
            traffic_limit_bytes=traffic_bytes,
            expiry_time=expiry_ms,
        )

        if not ok:
            await callback.message.answer(
                "❌ Ошибка при создании ключа. Обратись к администратору."
            )
            # Уведомляем админа
            for admin_id in ADMIN_TELEGRAM_IDS:
                try:
                    await bot.send_message(
                        admin_id,
                        f"⚠️ Ошибка создания ключа!\n"
                        f"User: {callback.from_user.id}\n"
                        f"Payment: {payment_id}",
                    )
                except Exception:
                    pass
            return

        # Создаём подписку в БД
        create_subscription(user["id"], plan_id, plan["duration_days"], plan["traffic_gb"])
        db_confirm_payment(payment_id)

        sub_link = get_sub_link(user["vpn_uuid"])
        text = (
            f"🎉 <b>Подписка активирована!</b>\n\n"
            f"📦 Тариф: {plan['name']}\n"
            f"📅 Срок: {plan['duration_days']} дн.\n\n"
            f"🔗 <b>Твоя ссылка подписки:</b>\n"
            f"<code>{sub_link}</code>\n\n"
            f"Скопируй и вставь в приложение.\n"
            f"Все серверы появятся автоматически! 🚀"
        )
        await callback.message.edit_text(text)

        # Уведомляем админа
        for admin_id in ADMIN_TELEGRAM_IDS:
            try:
                await bot.send_message(
                    admin_id,
                    f"💰 Новая оплата!\n"
                    f"User: @{callback.from_user.username} ({callback.from_user.id})\n"
                    f"Plan: {plan['name']} — {plan['price']}₽",
                )
            except Exception:
                pass

    elif result["status"] == "pending":
        await callback.answer("⏳ Оплата ещё не прошла. Подожди немного.", show_alert=True)
    elif result["status"] == "canceled":
        await callback.answer("❌ Платёж отменён.", show_alert=True)
    else:
        await callback.answer("⏳ Обрабатывается... Попробуй через минуту.", show_alert=True)


# ==================
# Мой ключ
# ==================

@router.callback_query(F.data == "mykey")
async def mykey_handler(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)
    sub = get_active_subscription(user["id"])

    if not sub:
        buttons = [
            [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy")],
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
        f"🔑 <b>Твой ключ SyntaxVPN</b>\n\n"
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
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="guide")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


# ==================
# Трафик
# ==================

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

    buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


# ==================
# Инструкция
# ==================

@router.callback_query(F.data == "guide")
async def guide_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📖 <b>Как подключиться?</b>\n\n"
        "<b>1.</b> Купи подписку или активируй пробный период\n"
        "<b>2.</b> Скопируй ссылку подписки (в разделе «Мой ключ»)\n"
        "<b>3.</b> Скачай приложение:\n\n"
        "📱 <b>Android:</b>\n"
        "• <a href='https://play.google.com/store/apps/details?id=com.v2ray.ang'>V2RayNG</a>\n"
        "• <a href='https://play.google.com/store/apps/details?id=app.hiddify.com'>Hiddify</a>\n\n"
        "🍎 <b>iOS:</b>\n"
        "• Streisand (App Store)\n"
        "• V2Box (App Store)\n\n"
        "💻 <b>Windows / macOS:</b>\n"
        "• <a href='https://github.com/hiddify/hiddify-app/releases'>Hiddify</a>\n\n"
        "<b>4.</b> В приложении: «Добавить» → «Подписка» → вставь ссылку\n"
        "<b>5.</b> Обнови подписку — появятся все серверы\n"
        "<b>6.</b> Выбери сервер и подключись! 🚀"
    )

    buttons = [[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)


# ==================
# Назад в меню
# ==================

@router.callback_query(F.data == "back_start")
async def back_start_handler(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)
    sub = get_active_subscription(user["id"])

    text = (
        f"👋 <b>SyntaxVPN</b>\n\n"
        f"🔒 Безопасный VPN с серверами в разных локациях.\n"
    )

    if sub:
        expires = datetime.fromisoformat(sub["expires_at"])
        days_left = (expires - datetime.utcnow()).days
        text += f"\n✅ Подписка активна | Осталось: <b>{days_left} дн.</b>\n"

    buttons = [
        [InlineKeyboardButton(text="🛒 Купить подписку", callback_data="buy")],
        [InlineKeyboardButton(text="🔑 Мой ключ", callback_data="mykey")],
        [InlineKeyboardButton(text="📊 Мой трафик", callback_data="traffic")],
        [InlineKeyboardButton(text="📖 Инструкция", callback_data="guide")],
    ]

    if callback.from_user.id in ADMIN_TELEGRAM_IDS:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


# ==================
# Админ-панель
# ==================

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
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


# ==================
# Запуск
# ==================

async def main():
    init_db()
    dp.include_router(router)
    logger.info("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
