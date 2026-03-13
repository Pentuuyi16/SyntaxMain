from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

from config import ADMIN_TELEGRAM_IDS, DOMAIN, SUB_PATH
from database import get_or_create_user, get_active_subscription, has_used_trial

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
    user = get_or_create_user(message.from_user.id, message.from_user.username)
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