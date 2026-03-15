from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from datetime import datetime, timedelta

from config import PLANS, ADMIN_TELEGRAM_IDS, DOMAIN, SUB_PATH
from config import TRIAL_ENABLED, TRIAL_DURATION_DAYS, TRIAL_TRAFFIC_GB
from database import (
    get_or_create_user,
    get_active_subscription,
    create_subscription,
    calculate_new_expiry,
    create_payment as db_create_payment,
    confirm_payment as db_confirm_payment,
    get_payment_by_yukassa_id,
    has_used_trial,
    mark_trial_used,
)
from xui_api import add_client_to_all_servers
from payments import create_payment as yk_create_payment, check_payment as yk_check_payment

router = Router()

BUY_VIDEO = "BAACAgIAAxkBAAID22m2pbPXv6wrFqHr0LQEZ5zDs7I5AALvpwACpBq4STjJPfOdA28OOgQ"


def get_sub_link(vpn_uuid: str) -> str:
    return f"https://{DOMAIN}{SUB_PATH}/{vpn_uuid}"


PLAN_LABELS = {
    "test": "1₽ - 1 день",
    "1month": "99₽ - 1 мес",
    "3month": "289₽ - 3 мес (🔥4%)",
    "6month": "549₽ - 6 мес (🔥8%)",
    "12month": "999₽ - 12 мес (🔥16%)",
}


def has_media(message) -> bool:
    return bool(message.photo or message.video or message.animation)


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

    email = f"tg_{callback.from_user.id}"
    traffic_bytes = TRIAL_TRAFFIC_GB * 1024 * 1024 * 1024
    expiry_ms = int((datetime.utcnow() + timedelta(days=TRIAL_DURATION_DAYS)).timestamp() * 1000)

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
    happ_redirect = f"https://{DOMAIN}/r?url={sub_link}"
    text = (
        f"Вы активировали пробную версию на {TRIAL_DURATION_DAYS} дня 🤍\n\n"
        f"🗝 Ключ:\n"
        f"<code>{sub_link}</code>"
    )
    buttons = [
        [InlineKeyboardButton(text="Добавить VPN в приложение", url=happ_redirect)],
        [InlineKeyboardButton(text="Установить приложение", callback_data="download_app")],
        [InlineKeyboardButton(text="🚪 Главное меню", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data == "buy")
async def buy_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📡 VPN‑ключ предоставляет доступ к стабильным локациям\n\n"
        "Идеален для YouTube, стриминга и онлайн-игр — "
        "всё летает без лагов и подвисаний.\n\n"
        "Instagram и TikTok открываются мгновенно, "
        "видео загружаются без ожидания — плавно, быстро и красиво.\n\n"
        "Стабильное соединение, которое уверенно обходит "
        "ограничения и глушилки — всегда на связи, без лишних проблем 🚀"
    )

    buttons = []
    for plan_id in PLAN_LABELS:
        buttons.append([InlineKeyboardButton(
            text=PLAN_LABELS[plan_id],
            callback_data=f"pay_{plan_id}"
        )])
    buttons.append([InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_video(video=BUY_VIDEO, caption=text, reply_markup=kb)


@router.callback_query(F.data.startswith("pay_"))
async def pay_handler(callback: CallbackQuery):
    await callback.answer()
    plan_id = callback.data.replace("pay_", "")

    if plan_id not in PLANS:
        await callback.message.answer("❌ Тариф не найден.")
        return

    plan = PLANS[plan_id]
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)

    payment = yk_create_payment(
        amount=plan["price"],
        plan_id=plan_id,
        telegram_id=callback.from_user.id,
        description=f"SyntaxVPN — {plan['name']}",
    )

    if not payment:
        await callback.message.answer("❌ Ошибка при создании платежа. Попробуй позже.")
        return

    db_create_payment(user["id"], plan_id, plan["price"], payment["payment_id"])

    buttons = [
        [InlineKeyboardButton(text=f"Оплатить {plan['price']}₽", url=payment["confirmation_url"])],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="buy")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    text = (
        f"<b>🕊 Свобода всё ближе!</b>\n\n"
        f"<b>Подтверждение об успешной оплате приходит в течение нескольких секунд</b>"
    )
    if has_media(callback.message):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)


@router.callback_query(F.data.startswith("check_"))
async def check_payment_handler(callback: CallbackQuery):
    from bot import bot

    payment_id = callback.data.replace("check_", "")
    result = yk_check_payment(payment_id)

    if result["status"] == "succeeded" and result["paid"]:
        await callback.answer("✅ Оплата подтверждена!")

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

        new_expires = calculate_new_expiry(user["id"], plan["duration_days"])
        expiry_ms = int(new_expires.timestamp() * 1000)
        traffic_bytes = plan["traffic_gb"] * 1024 * 1024 * 1024 if plan["traffic_gb"] > 0 else 0

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

        create_subscription(user["id"], plan_id, plan["duration_days"], plan["traffic_gb"])
        db_confirm_payment(payment_id)

        sub_link = get_sub_link(user["vpn_uuid"])
        text = (
            f"<b>Готово! Оплата подтверждена ✅</b>\n\n"
            f"Спасибо, что выбрали нас — это много значит для нашей команды.\n\n"
            f"<b>С любовью, SyntaxVPN 🤍</b>\n\n"
            f"<b>Ваш ключ, нажмите чтобы скопировать:</b>\n"
            f"<code>{sub_link}</code>"
        )
        buttons = [
            [InlineKeyboardButton(text="🚪 Главное меню", callback_data="back_start")],
        ]
        kb = InlineKeyboardMarkup(inline_keyboard=buttons)
        if has_media(callback.message):
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.message.answer(text, reply_markup=kb)
        else:
            try:
                await callback.message.edit_text(text, reply_markup=kb)
            except Exception:
                await callback.message.answer(text, reply_markup=kb)

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


@router.callback_query(F.data == "download_app")
async def download_app_handler(callback: CallbackQuery):
    await callback.answer()

    text = "📱 <b>Выберите тип вашего устройства</b>"

    buttons = [
        [InlineKeyboardButton(text="🍎 iOS", url="https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973")],
        [InlineKeyboardButton(text="🤖 Android", url="https://play.google.com/store/search?q=Happ&c=apps&hl=ru")],
        [InlineKeyboardButton(text="💻 Windows", url="https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe")],
        [InlineKeyboardButton(text="🚪 Главное меню", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)

    if has_media(callback.message):
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.message.answer(text, reply_markup=kb)
    else:
        try:
            await callback.message.edit_text(text, reply_markup=kb)
        except Exception:
            await callback.message.answer(text, reply_markup=kb)