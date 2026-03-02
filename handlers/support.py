from aiogram import Router, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery

router = Router()


@router.callback_query(F.data == "support")
async def support_handler(callback: CallbackQuery):
    await callback.answer()

    text = "🎧 <b>Поддержка Syntax VPN</b>"

    buttons = [
        [InlineKeyboardButton(text="🔌 Как подключить VPN?", callback_data="how_to_connect")],
        [InlineKeyboardButton(text="⁉️ Часто задаваемые вопросы", callback_data="faq")],
        [InlineKeyboardButton(text="🎧 Чат с поддержкой", callback_data="chat_support")],
        [InlineKeyboardButton(text="🚪 Назад", callback_data="back_start")],
    ]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "faq")
async def faq_handler(callback: CallbackQuery):
    await callback.answer()

    text = (
        "♟ Здесь собраны ответы на самые популярные вопросы.\n\n"
        "<b>Мои данные в безопасности?</b>\n"
        "— Да. Ваша информация под надёжной защитой. "
        "Мы применяем современные протоколы шифрования, "
        "благодаря которым доступ к трафику для третьих лиц исключён.\n\n"
        "<b>Говорят, что VPN может передавать или красть данные.</b>\n"
        "— Такое возможно у недобросовестных сервисов. "
        "Мы работаем на репутацию и долгосрочное сотрудничество, "
        "поэтому не имеем доступа к вашему зашифрованному трафику "
        "и не собираем личную информацию.\n\n"
        "<b>Есть ли ограничения по подписке?</b>\n"
        "— Да, предусмотрены лимиты: до 2 устройств на один ключ."
    )

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "how_to_connect")
async def how_to_connect_handler(callback: CallbackQuery):
    await callback.answer()

    text = "🔌 <b>Как подключить VPN?</b>\n\n🚧 Раздел в разработке."

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)


@router.callback_query(F.data == "chat_support")
async def chat_support_handler(callback: CallbackQuery):
    await callback.answer()

    text = "🎧 <b>Чат с поддержкой</b>\n\n🚧 Раздел в разработке."

    buttons = [[InlineKeyboardButton(text="🚪 Назад", callback_data="support")]]
    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(text, reply_markup=kb)