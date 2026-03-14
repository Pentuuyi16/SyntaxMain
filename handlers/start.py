from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import ADMIN_TELEGRAM_IDS, DOMAIN, SUB_PATH, REFERRAL_BONUS_DAYS
from database import (
    get_or_create_user,
    get_active_subscription,
    has_used_trial,
    get_user_by_telegram_id,
    add_referral,
    extend_subscription,
    create_subscription,
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
        f"Подписывайтесь на наш <a href='https://t.me/AllenVPN'>канал</a>, "
        f"чтобы быть в курсе последних событий."
    )


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    from bot import bot

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

    # Проверяем — новый ли это пользователь
    existing_user = get_user_by_telegram_id(message.from_user.id)
    is_new_user = existing_user is None

    user = get_or_create_user(message.from_user.id, message.from_user.username, referred_by=referrer_id)

    # Начисляем бонус рефереру если новый пользователь пришёл по ссылке
    if is_new_user and referrer_id:
        referrer = get_user_by_telegram_id(referrer_id)
        if referrer:
            added = add_referral(referrer_id, message.from_user.id, bonus_days=REFERRAL_BONUS_DAYS)
            if added:
                referrer_user = get_or_create_user(referrer_id)
                sub = get_active_subscription(referrer_user["id"])

                if sub:
                    # Есть подписка — продлеваем
                    extend_subscription(referrer_user["id"], REFERRAL_BONUS_DAYS)
                else:
                    # Нет подписки — создаём новую и добавляем ключ на серверы
                    email = f"tg_{referrer_id}"
                    from datetime import datetime, timedelta
                    expiry_ms = int(
                        (datetime.utcnow() + timedelta(days=REFERRAL_BONUS_DAYS)).timestamp() * 1000
                    )
                    await add_client_to_all_servers(
                        vpn_uuid=referrer_user["vpn_uuid"],
                        email=email,
                        traffic_limit_bytes=0,
                        expiry_time=expiry_ms,
                    )
                    create_subscription(referrer_user["id"], "referral", REFERRAL_BONUS_DAYS, 0)

                try:
                    sub_link = f"https://{DOMAIN}{SUB_PATH}/{referrer_user['vpn_uuid']}"
                    await bot.send_message(
                        referrer_id,
                        f"🎉 Ваш друг присоединился по реферальной ссылке!\n"
                        f"Вам начислено <b>+{REFERRAL_BONUS_DAYS} дня</b> к подписке!\n\n"
                        f"🗝 Ваш ключ:\n"
                        f"<code>{sub_link}</code>",
                    )
                except Exception:
                    pass

    first_name = message.from_user.first_name or "друг"
    text = get_welcome_text(first_name)
    sub = get_active_subscription(user["id"])
    show_trial = not has_used_trial(message.from_user.id) and not sub
    kb = get_main_menu(message.from_user.id, show_trial=show_trial)
    await message.answer_video(video=WELCOME_VIDEO, caption=text, reply_markup=kb)


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