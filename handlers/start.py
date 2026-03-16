from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from datetime import datetime, timedelta

from config import ADMIN_TELEGRAM_IDS, DOMAIN, SUB_PATH, REFERRAL_BONUS_DAYS
from database import (
    get_or_create_user,
    get_active_subscription,
    has_used_trial,
    get_user_by_telegram_id,
    add_referral,
    extend_subscription,
    create_subscription,
    calculate_new_expiry,
)
from xui_api import add_client_to_all_servers

router = Router()

WELCOME_VIDEO = "BAACAgIAAxkBAAPTabG1FttZVJgs48wZqknWfFKmf70AAjyfAAJaVpBJzPjJ_XuBX6o6BA"


def get_main_menu(user_id: int, show_trial: bool = False) -> InlineKeyboardMarkup:
    buttons = []

    if show_trial:
        buttons.append([InlineKeyboardButton(text="🎁 Бесплатный пробный период", callback_data="trial")])

    buttons.append([InlineKeyboardButton(text="🤍 Купить подписку", callback_data="buy")])
    buttons.append([
        InlineKeyboardButton(text="🔑 Мои ключи", callback_data="mykey"),
        InlineKeyboardButton(text="🎧 Поддержка", callback_data="support"),
    ])
    buttons.append([InlineKeyboardButton(text="🔌 Как подключить VPN?", callback_data="how_to_connect_main")])
    buttons.append([InlineKeyboardButton(text="👾 Реферальная система", callback_data="referral")])

    if user_id in ADMIN_TELEGRAM_IDS:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_welcome_text(first_name: str) -> str:
    return (
        f"<b>Syntax VPN - Дорога к свободе</b> 🕊\n\n"
        f"👋 Добро пожаловать, {first_name}!\n\n"
        f"Мы обеспечиваем стабильный и безопасный доступ к интернету "
        f"каждый день, предлагая честные цены и выгодные тарифы.\n\n"
        f"Подписывайтесь на наш <a href='https://t.me/syntxvpn'>канал</a>, "
        f"чтобы быть в курсе последних событий."
    )


async def give_referral_bonus(referrer_id: int, referrer_user: dict):
    """Начисляет реферальный бонус — продлевает или создаёт подписку + обновляет панель"""
    from bot import bot

    sub = get_active_subscription(referrer_user["id"])

    if sub:
        # Есть подписка — продлеваем в базе
        new_expires = extend_subscription(referrer_user["id"], REFERRAL_BONUS_DAYS)
        expiry_ms = int(new_expires.timestamp() * 1000)
    else:
        # Нет подписки — создаём новую
        create_subscription(referrer_user["id"], "referral", REFERRAL_BONUS_DAYS, 0)
        new_sub = get_active_subscription(referrer_user["id"])
        new_expires = datetime.fromisoformat(new_sub["expires_at"])
        expiry_ms = int(new_expires.timestamp() * 1000)

    # Обновляем expiryTime на всех серверах
    email = f"tg_{referrer_id}"
    await add_client_to_all_servers(
        vpn_uuid=referrer_user["vpn_uuid"],
        email=email,
        traffic_limit_bytes=0,
        expiry_time=expiry_ms,
    )

    try:
        sub_link = f"https://{DOMAIN}{SUB_PATH}/{referrer_user['vpn_uuid']}"
        happ_redirect = f"https://{DOMAIN}/r?url={sub_link}"
        buttons = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Добавить VPN в приложение", url=happ_redirect)],
            [InlineKeyboardButton(text="🚪 Главное меню", callback_data="back_start")],
        ])
        await bot.send_message(
            referrer_id,
            f"🎉 Ваш друг присоединился по реферальной ссылке!\n"
            f"Вам начислено <b>+{REFERRAL_BONUS_DAYS} дня</b> к подписке!\n\n"
            f"🗝 Ваш ключ:\n"
            f"<code>{sub_link}</code>",
            reply_markup=buttons,
        )
    except Exception:
        pass


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    # Проверяем реферальную ссылку
    referrer_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].replace("ref_", ""))
            if referrer_id == message.from_user.id:
                referrer_id = None
        except ValueError:
            referrer_id = None

    existing_user = get_user_by_telegram_id(message.from_user.id)
    is_new_user = existing_user is None

    user = get_or_create_user(message.from_user.id, message.from_user.username, referred_by=referrer_id)

    # Начисляем бонус рефереру
    if is_new_user and referrer_id:
        referrer = get_user_by_telegram_id(referrer_id)
        if referrer:
            added = add_referral(referrer_id, message.from_user.id, bonus_days=REFERRAL_BONUS_DAYS)
            if added:
                referrer_user = get_or_create_user(referrer_id)
                await give_referral_bonus(referrer_id, referrer_user)

    first_name = message.from_user.first_name or "друг"
    text = get_welcome_text(first_name)
    sub = get_active_subscription(user["id"])
    show_trial = not has_used_trial(message.from_user.id) and not sub
    kb = get_main_menu(message.from_user.id, show_trial=show_trial)
    await message.answer_video(video=WELCOME_VIDEO, caption=text, reply_markup=kb)

@router.callback_query(F.data == "how_to_connect_main")
async def how_to_connect_main_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "📃 <b>Инструкция по подключению</b>\n\n"
        "⚖️ <b>Шаг 1. Установите приложение</b>\n"
        "Скачайте VPN-клиент:\n"
        "• <a href='https://play.google.com/store/search?q=Happ&c=apps&hl=ru'>Happ — Android</a>\n"
        "• <a href='https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973'>Happ — iOS</a>\n"
        "• <a href='https://github.com/Happ-proxy/happ-desktop/releases/latest/download/setup-Happ.x64.exe'>Happ — Windows</a>\n\n"
        "🔑 <b>Шаг 2. Импортируйте ключ</b>\n"
        "Откройте раздел «Мой ключ» и нажмите кнопку "
        "«Добавить VPN в приложение» (только если вы установили Happ), "
        "можно и вручную скопировать ключ и вставить\n\n"
        "🎉 <b>Шаг 3. Подключение</b>\n"
        "Готово! Пользуйтесь быстрым и безопасным интернетом 🚀\n\n"
        "🧾 В случае проблем с подключением помощь можно будет "
        "найти в разделе «🎧 Поддержка»"
    )

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer(text, reply_markup=kb, disable_web_page_preview=True)

@router.callback_query(F.data == "back_start")
async def back_start_handler(callback: CallbackQuery):
    await callback.answer()
    user = get_or_create_user(callback.from_user.id, callback.from_user.username)
    first_name = callback.from_user.first_name or "друг"
    text = get_welcome_text(first_name)
    sub = get_active_subscription(user["id"])
    show_trial = not has_used_trial(callback.from_user.id) and not sub
    kb = get_main_menu(callback.from_user.id, show_trial=show_trial)

    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.message.answer_video(video=WELCOME_VIDEO, caption=text, reply_markup=kb)