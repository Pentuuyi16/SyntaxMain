from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery, InputMediaPhoto

from config import ADMIN_TELEGRAM_IDS
from database import get_or_create_user, get_active_subscription

router = Router()

WELCOME_PHOTO = "AgACAgIAAxkBAAOzabB-82YQ4nLfLDvh4yDJHLlvh20AAg8UaxtaVohJPKOiJa0997wBAAMCAAN5AAM6BA"


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
    kb = get_main_menu(message.from_user.id)
    await message.answer_photo(photo=WELCOME_PHOTO, caption=text, reply_markup=kb)


@router.callback_query(F.data == "back_start")
async def back_start_handler(callback: CallbackQuery):
    await callback.answer()
    first_name = callback.from_user.first_name or "друг"
    text = get_welcome_text(first_name)
    kb = get_main_menu(callback.from_user.id)

    if callback.message.photo:
        await callback.message.edit_caption(caption=text, reply_markup=kb)
    else:
        await callback.message.delete()
        await callback.message.answer_photo(photo=WELCOME_PHOTO, caption=text, reply_markup=kb)