from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from datetime import datetime

from config import ADMIN_TELEGRAM_IDS
from database import get_or_create_user, get_active_subscription

router = Router()


def get_main_menu(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🤍 Купить подписку", callback_data="buy")],
        [
            InlineKeyboardButton(text="🔑 Мои ключи", callback_data="mykey"),
            InlineKeyboardButton(text="🎧 Поддержка", callback_data="support"),
        ],
        [InlineKeyboardButton(text="👾 Реферальная система", callback_data="referral")],
    ]

    if user_id in ADMIN_TELEGRAM_IDS:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(CommandStart())
async def cmd_start(message: types.Message):
    user = get_or_create_user(message.from_user.id, message.from_user.username)

    first_name = message.from_user.first_name or "друг"
    text = (
        f"<b>Syntax VPN - Дорога к свободе</b> 🕊\n\n"
        f"👋 Добро пожаловать, {first_name}!\n\n"
        f"Мы обеспечиваем стабильный и безопасный доступ к интернету "
        f"каждый день, предлагая честные цены и выгодные тарифы.\n\n"
        f"Подписывайтесь на наш <a href='https://t.me/AllenVPN'>канал</a>, "
        f"чтобы быть в курсе последних событий."
    )

    kb = get_main_menu(message.from_user.id)
    await message.answer(text, reply_markup=kb, disable_web_page_preview=True)


@router.callback_query(F.data == "back_start")
async def back_start_handler(callback: CallbackQuery):
    await callback.answer()

    first_name = callback.from_user.first_name or "друг"
    text = (
        f"<b>Syntax VPN - Дорога к свободе</b> 🕊\n\n"
        f"👋 С возвращением, {first_name}!\n\n"
        f"Мы обеспечиваем стабильный и безопасный доступ к интернету "
        f"каждый день, предлагая честные цены и выгодные тарифы.\n\n"
        f"Подписывайтесь на наш <a href='https://t.me/AllenVPN'>канал</a>, "
        f"чтобы быть в курсе последних событий."
    )

    kb = get_main_menu(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)